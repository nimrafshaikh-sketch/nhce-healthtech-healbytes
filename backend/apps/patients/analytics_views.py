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
from apps.medications.models import Medication, MedicationReminderLog

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


def _build_analytics(patient):
    checkins = DailyCheckin.objects.filter(patient=patient)
    reminders = MedicationReminderLog.objects.filter(medication__patient=patient)
    alerts = Alert.objects.filter(patient=patient)

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


@extend_schema(tags=["Analytics"], summary="Doctor: AI-computed clinical history summary for an assigned patient")
class PatientAISummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id, doctor=request.user)
        summary = get_patient_history_summary(patient)
        if summary is None:
            return Response(
                {"detail": "AI engine is currently unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(summary)


@extend_schema(tags=["Analytics"], summary="Patient: AI-computed clinical history summary for self")
class MyAISummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get(self, request):
        patient = get_object_or_404(Patient, user=request.user)
        summary = get_patient_history_summary(patient)
        if summary is None:
            return Response(
                {"detail": "AI engine is currently unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(summary)
