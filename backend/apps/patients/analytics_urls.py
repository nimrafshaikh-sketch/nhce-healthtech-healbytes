from django.urls import path

from . import analytics_views

urlpatterns = [
    path("me/", analytics_views.MyAnalyticsView.as_view(), name="analytics-me"),
    path("patients/<int:patient_id>/", analytics_views.PatientAnalyticsView.as_view(), name="analytics-patient"),
]
