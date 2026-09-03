from django.urls import path

from . import views

urlpatterns = [
    path("", views.CheckinListCreateView.as_view(), name="checkin-list-create"),
    path("<int:pk>/", views.CheckinDetailView.as_view(), name="checkin-detail"),
]
