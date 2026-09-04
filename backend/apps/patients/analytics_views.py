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
from apps.medications.models import Medication, MedicationReminderLog, Prescription

from .models import Patient


class CheckinAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_risk_level = serializers.DictField(child=serializers.IntegerField())


class MedicationAnalyticsSerializer(serializers.Serializer):
    active_count = serializers.IntegerField()
    reminders_sent = serializers.IntegerField()
    reminders_acknowledged = serializers.IntegerField()


class AlertAnalyticsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    open = serializers.IntegerField()
    by_severity = serializers.DictField(child=serializers.IntegerField())


class PatientAnalyticsSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    checkins = CheckinAnalyticsSerializer()
    medications = MedicationAnalyticsSerializer()
    alerts = AlertAnalyticsSerializer()
    most_recent_lab_result = serializers.JSONField(allow_null=True, required=False)
    most_recent_prescription = serializers.JSONField(allow_null=True, required=False)
    days_since_last_checkin = serializers.IntegerField(allow_null=True, required=False)


def _build_analytics(patient):
    from django.utils import timezone
    from apps.labtests.models import LabTestResult

    checkins = DailyCheckin.objects.filter(patient=patient)
    reminders = MedicationReminderLog.objects.filter(medication__patient=patient)
    alerts = Alert.objects.filter(patient=patient)

    latest_checkin = checkins.order_by("-checkin_date", "-created_at").first()
    days_since = (timezone.localdate() - latest_checkin.checkin_date).days if latest_checkin else None

    latest_lab = (
        LabTestResult.objects.filter(request__patient=patient)
        .select_related("request")
        .order_by("-created_at")
        .first()
    )
    most_recent_lab = None
    if latest_lab:
        most_recent_lab = {
            "id": latest_lab.id,
            "request_id": latest_lab.request_id,
            "test_name": latest_lab.request.get_test_name_display() if hasattr(latest_lab.request, "get_test_name_display") else str(latest_lab.request.test_name),
            "status": latest_lab.request.status,
            "result_text": latest_lab.result_text,
            "reviewed_at": latest_lab.reviewed_at.isoformat() if latest_lab.reviewed_at else None,
            "created_at": latest_lab.created_at.isoformat() if latest_lab.created_at else None,
        }

    latest_prescription = Prescription.objects.filter(patient=patient).order_by("-created_at").first()
    most_recent_prescription_data = None
    if latest_prescription:
        most_recent_prescription_data = {
            "id": latest_prescription.id,
            "medication_name": latest_prescription.medication_name,
            "dosage": latest_prescription.dosage,
            "frequency": latest_prescription.frequency,
            "doctor": latest_prescription.doctor.get_full_name() if latest_prescription.doctor else None,
            "created_at": latest_prescription.created_at.isoformat() if latest_prescription.created_at else None,
        }

    return {
        "patient_id": patient.id,
        "checkins": {
            "total": checkins.count(),
            "by_risk_level": dict(
                checkins.values_list("ai_risk_level").annotate(count=Count("id")).order_by()
            ),
        },
        "medications": {
            "active_count": Medication.objects.filter(patient=patient, is_active=True).count(),
            "reminders_sent": reminders.count(),
            "reminders_acknowledged": reminders.filter(acknowledged_at__isnull=False).count(),
        },
        "alerts": {
            "total": alerts.count(),
            "open": alerts.filter(status=Alert.Status.OPEN).count(),
            "by_severity": dict(
                alerts.values_list("severity").annotate(count=Count("id")).order_by()
            ),
        },
        "days_since_last_checkin": days_since,
        "most_recent_lab_result": most_recent_lab,
        "most_recent_prescription": most_recent_prescription_data,
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


from apps.patients.timeline import build_patient_timeline


@extend_schema(tags=["Analytics"], summary="Doctor: unified chronological Patient Timeline for an assigned patient")
class PatientTimelineView(APIView):
    """Phase 4 - deterministic aggregation of real events (appointments,
    prescriptions, labs, check-ins, AI evaluations, documents) into one
    chronological view. See apps.patients.timeline module docstring."""
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
        return Response(build_patient_timeline(patient))


@extend_schema(tags=["Analytics"], summary="Patient: unified chronological timeline for self")
class MyTimelineView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get(self, request):
        patient = get_object_or_404(Patient, user=request.user)
        return Response(build_patient_timeline(patient))
