from django.urls import path

from . import views

urlpatterns = [
    path("", views.MedicationListCreateView.as_view(), name="medication-list-create"),
    path("<int:pk>/", views.MedicationDetailView.as_view(), name="medication-detail"),
    path("<int:medication_id>/adherence/", views.MedicationAdherenceListView.as_view(), name="medication-adherence"),
    path("adherence/<int:pk>/update/", views.UpdateAdherenceView.as_view(), name="adherence-update"),
]
