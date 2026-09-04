from django.urls import path

from . import views

urlpatterns = [
    path("", views.MedicationListCreateView.as_view(), name="medication-list-create"),
    path("<int:pk>/", views.MedicationDetailView.as_view(), name="medication-detail"),
    path("<int:medication_id>/reminders/", views.MedicationReminderLogListView.as_view(), name="medication-reminders"),
    path("reminders/<int:pk>/acknowledge/", views.AcknowledgeReminderView.as_view(), name="reminder-acknowledge"),
    path("prescriptions/", views.PrescriptionListCreateView.as_view(), name="prescription-list-create"),
    path("prescriptions/<int:pk>/", views.PrescriptionDetailView.as_view(), name="prescription-detail"),
    path("intelligence/", views.MedicationIntelligenceView.as_view(), name="medication-intelligence"),
]
