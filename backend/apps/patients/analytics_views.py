"""Basic history/analytics and AI history summary endpoints.

Doctor can view any of their assigned patients; a patient can only view their own.
"""
from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.checkins.ai_client import get_patient_history_summary
from apps.checkins.models import DailyCheckin
from apps.core.permissions import IsDoctor, IsPatient
from apps.labtests.models import LabTestResult
from apps.medications.models import Medication, MedicationAdherence

from .models import Patient


class CheckinAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_risk_level = serializers.DictField(child=serializers.IntegerField())


class MedicationAnalyticsSerializer(serializers.Serializer):
    active_count = serializers.IntegerField()
    scheduled_doses = serializers.IntegerField()
    doses_taken = serializers.IntegerField()


class AlertAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    unread = serializers.IntegerField()
    by_risk_level = serializers.DictField(child=serializers.IntegerField())


class PatientAnalyticsSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    checkins = CheckinAnalyticsSerializer()
    medications = MedicationAnalyticsSerializer()
    alerts = AlertAnalyticsSerializer()
    most_recent_lab_result = serializers.JSONField(allow_null=True)
    most_recent_prescription = serializers.JSONField(allow_null=True)
    days_since_last_checkin = serializers.IntegerField(allow_null=True)


def _build_analytics(patient):
    checkins = DailyCheckin.objects.filter(patient=patient)
    adherence = MedicationAdherence.objects.filter(medication__patient=patient)
    alerts = Alert.objects.filter(patient=patient)

    from django.utils import timezone
    now_date = timezone.localdate()

    # Active medications = end_date is null or in the future
    from django.db.models import Q
    active_meds = Medication.objects.filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now_date),
        patient=patient
    )

    # --- days_since_last_checkin (Member 3 / P1) ---------------------------
    # Deterministic PostgreSQL-derived value, never fabricated: None (not 0)
    # when the patient has no check-in on record at all.
    latest_checkin = checkins.order_by("-checkin_date", "-created_at").first()
    days_since_last_checkin = (
        (now_date - latest_checkin.checkin_date).days if latest_checkin else None
    )

    # --- most_recent_lab_result (Member 3 / P1) -----------------------------
    # LabTestResult -> LabTestRequest -> Patient. Only real fields from the
    # actual apps.labtests models (verified against Member 2's models.py) -
    # nothing invented, no unrelated clinical detail exposed.
    latest_lab_result = (
        LabTestResult.objects.filter(request__patient=patient)
        .select_related("request")
        .order_by("-created_at")
        .first()
    )
    most_recent_lab_result = (
        {
            "test_name": latest_lab_result.request.get_test_name_display(),
            "status": latest_lab_result.request.status,
            "result_text": latest_lab_result.result_text,
            "recorded_at": latest_lab_result.created_at,
            "reviewed_at": latest_lab_result.reviewed_at,
        }
        if latest_lab_result else None
    )

    return {
        "patient_id": patient.id,
        "checkins": {
            "total": checkins.count(),
            "by_risk_level": dict(
                checkins.values_list("ai_risk_level").annotate(count=Count("id")).order_by()
            ),
        },
        "medications": {
            "active_count": active_meds.count(),
            "scheduled_doses": adherence.count(),
            "doses_taken": adherence.filter(status=MedicationAdherence.Status.TAKEN).count(),
        },
        "alerts": {
            "total": alerts.count(),
            "unread": alerts.filter(status=Alert.Status.UNREAD).count(),
            "by_risk_level": dict(
                alerts.values_list("risk_level").annotate(count=Count("id")).order_by()
            ),
        },
        # --- Member 3 / P1 additions: structured input for Member 4's
        # History/Summary agent. Shape is stable (keys always present);
        # values are None ("not available"), never a fabricated placeholder.
        #
        # most_recent_prescription stays None: Prescription doesn't exist as
        # a Django model anywhere in this repo yet (Member 2 hasn't added it).
        # Wire the real query here once that model lands; do not guess its
        # field shape in the meantime.
        "most_recent_lab_result": most_recent_lab_result,
        "most_recent_prescription": None,
        "days_since_last_checkin": days_since_last_checkin,
    }


@extend_schema(tags=["Analytics"], summary="Doctor: aggregate counters for one of their patients",
               responses=PatientAnalyticsSerializer)
class PatientAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
        return Response(_build_analytics(patient))


@extend_schema(tags=["Analytics"], summary="Patient: aggregate counters for the logged-in patient",
               responses=PatientAnalyticsSerializer)
class MyAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get(self, request):
        patient = get_object_or_404(Patient, user=request.user)
        return Response(_build_analytics(patient))


from apps.patients.clinical_brief import build_clinical_brief


@extend_schema(tags=["Analytics"], summary="Doctor: AI-computed clinical history summary & grounded brief for an assigned patient")
class PatientAISummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
        clinical_brief_data = build_clinical_brief(patient)
        ai_engine_summary = get_patient_history_summary(patient)

        result = {
            **clinical_brief_data,
            "ai_engine_summary": ai_engine_summary,
        }
        if ai_engine_summary and "history" in ai_engine_summary:
            result["history"] = ai_engine_summary["history"]
            result["request_id"] = ai_engine_summary.get("request_id")
        return Response(result)


@extend_schema(tags=["Analytics"], summary="Patient: AI-computed clinical history summary for self")
class MyAISummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get(self, request):
        patient = get_object_or_404(Patient, user=request.user)
        clinical_brief_data = build_clinical_brief(patient)
        ai_engine_summary = get_patient_history_summary(patient)

        result = {
            **clinical_brief_data,
            "ai_engine_summary": ai_engine_summary,
        }
        if ai_engine_summary and "history" in ai_engine_summary:
            result["history"] = ai_engine_summary["history"]
            result["request_id"] = ai_engine_summary.get("request_id")
        return Response(result)
