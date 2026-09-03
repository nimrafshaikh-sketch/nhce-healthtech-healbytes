from django.urls import path

from . import views

urlpatterns = [
    path("", views.AlertListView.as_view(), name="alert-list"),
    path("<int:pk>/acknowledge/", views.AlertAcknowledgeView.as_view(), name="alert-acknowledge"),
    path("<int:pk>/resolve/", views.AlertResolveView.as_view(), name="alert-resolve"),
]
