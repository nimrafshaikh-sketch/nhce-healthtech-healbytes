from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor

from .models import Alert
from .serializers import AlertSerializer


@extend_schema(tags=["Alerts"], summary="List alerts for the logged-in doctor's patients")
class AlertListView(generics.ListAPIView):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get_queryset(self):
        qs = Alert.objects.filter(patient__doctor=self.request.user).select_related("patient")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


@extend_schema(tags=["Alerts"], summary="Acknowledge an alert (Doctor only)", request=None, responses=AlertSerializer)
class AlertAcknowledgeView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        alert = generics.get_object_or_404(Alert, pk=pk, patient__doctor=request.user)
        alert.status = Alert.Status.ACKNOWLEDGED
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save(update_fields=["status", "acknowledged_by", "acknowledged_at"])
        return Response(AlertSerializer(alert).data)


@extend_schema(tags=["Alerts"], summary="Resolve an alert (Doctor only)", request=None, responses=AlertSerializer)
class AlertResolveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        alert = generics.get_object_or_404(Alert, pk=pk, patient__doctor=request.user)
        alert.status = Alert.Status.RESOLVED
        alert.save(update_fields=["status"])
        return Response(AlertSerializer(alert).data)
