from django.urls import path

from . import views

urlpatterns = [
    path("", views.AppointmentListCreateView.as_view(), name="appointment-list-create"),
    path("<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment-detail"),
    path("<int:pk>/confirm/", views.AppointmentConfirmView.as_view(), name="appointment-confirm"),
    path("<int:pk>/cancel/", views.AppointmentCancelView.as_view(), name="appointment-cancel"),
]
