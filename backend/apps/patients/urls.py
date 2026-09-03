from django.urls import path

from . import views

urlpatterns = [
    path("", views.PatientListCreateView.as_view(), name="patient-list-create"),
    path("me/", views.MyPatientProfileView.as_view(), name="patient-me"),
    path("<int:pk>/", views.PatientDetailView.as_view(), name="patient-detail"),
]
