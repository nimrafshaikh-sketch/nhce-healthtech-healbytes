from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor, IsPatient

from .models import EmailNotificationLog, Notification
from .serializers import EmailNotificationLogSerializer, NotificationSerializer


@extend_schema(tags=["Notifications"], summary="List the logged-in user's in-app notifications")
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        unread_only = self.request.query_params.get("unread") == "true"
        if unread_only:
            qs = qs.filter(read_at__isnull=True)
        return qs


@extend_schema(tags=["Notifications"], summary="Mark a notification as read", request=None,
               responses=NotificationSerializer)
class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = generics.get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.read_at:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


@extend_schema(tags=["Notifications"], summary="Doctor: list email notifications sent for their patients "
                                                 "(doctor alerts, caretaker updates, patient reminders/results)")
class EmailNotificationLogListView(generics.ListAPIView):
    """Audit trail for all outbound emails tied to the doctor's own patients -
    regardless of who the recipient was (doctor/patient/caretaker)."""
    serializer_class = EmailNotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get_queryset(self):
        qs = EmailNotificationLog.objects.filter(patient__doctor=self.request.user.doctor_profile)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        recipient_type = self.request.query_params.get("recipient_type")
        if recipient_type:
            qs = qs.filter(recipient_type=recipient_type)
        return qs


@extend_schema(tags=["Notifications"], summary="Patient: list emails sent to the logged-in patient "
                                                 "(their own check-in results, medication reminders)")
class MyEmailNotificationLogListView(generics.ListAPIView):
    serializer_class = EmailNotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get_queryset(self):
        return EmailNotificationLog.objects.filter(
            recipient_type=EmailNotificationLog.RecipientType.PATIENT,
            recipient_user=self.request.user,
        )
