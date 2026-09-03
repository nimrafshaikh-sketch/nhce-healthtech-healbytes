from django.urls import path

from . import views

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/read/", views.NotificationMarkReadView.as_view(), name="notification-read"),
    path("email-logs/", views.EmailNotificationLogListView.as_view(), name="email-notification-log-list"),
    path("email-logs/me/", views.MyEmailNotificationLogListView.as_view(), name="email-notification-log-me"),
]
