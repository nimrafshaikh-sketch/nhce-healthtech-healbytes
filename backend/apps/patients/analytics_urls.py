from django.urls import path

from . import analytics_views

urlpatterns = [
    path("me/", analytics_views.MyAnalyticsView.as_view(), name="analytics-me"),
    path("me/ai-summary/", analytics_views.MyAISummaryView.as_view(), name="analytics-me-ai-summary"),
    path("patients/<int:patient_id>/", analytics_views.PatientAnalyticsView.as_view(), name="analytics-patient"),
    path("patients/<int:patient_id>/ai-summary/", analytics_views.PatientAISummaryView.as_view(), name="analytics-patient-ai-summary"),
]
