"""Basic history/analytics endpoints.

Deliberately simple aggregate counts/trends over existing data - NOT medical
risk analysis (that stays in the separate AI engine, per scope). Doctor can
view any of their own patients; a patient can only view their own.
"""
from django.db.models import Count
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.checkins.models import DailyCheckin
from apps.core.permissions import IsDoctor, IsPatient
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
        # most_recent_lab_result / most_recent_prescription are None for now:
        # LabResult and Prescription don't exist as Django models anywhere in
        # this repo yet (Member 2 hasn't added them - see Member 3's report).
        # Wire the real query here once those models land; do not guess their
        # field shape in the meantime.
        "most_recent_lab_result": None,
        "most_recent_prescription": None,
        "days_since_last_checkin": days_since_last_checkin,
    }


@extend_schema(tags=["Analytics"], summary="Doctor: analytics/history summary for one of their patients",
               responses=PatientAnalyticsSerializer)
class PatientAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
        return Response(_build_analytics(patient))


@extend_schema(tags=["Analytics"], summary="Patient: analytics/history summary for the logged-in patient",
               responses=PatientAnalyticsSerializer)
class MyAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get(self, request):
        patient = get_object_or_404(Patient, user=request.user)
        return Response(_build_analytics(patient))
