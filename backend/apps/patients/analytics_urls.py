from django.urls import path

from . import analytics_views

urlpatterns = [
    path("me/", analytics_views.MyAnalyticsView.as_view(), name="analytics-me"),
    path("me/ai-summary/", analytics_views.MyAISummaryView.as_view(), name="analytics-me-ai-summary"),
    path("patients/<int:patient_id>/", analytics_views.PatientAnalyticsView.as_view(), name="analytics-patient"),
    path("patients/<int:patient_id>/ai-summary/", analytics_views.PatientAISummaryView.as_view(), name="analytics-patient-ai-summary"),
    path("me/timeline/", analytics_views.MyTimelineView.as_view(), name="analytics-me-timeline"),
    path("patients/<int:patient_id>/timeline/", analytics_views.PatientTimelineView.as_view(), name="analytics-patient-timeline"),
]
