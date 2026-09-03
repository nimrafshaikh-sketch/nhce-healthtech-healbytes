"""
Root URL configuration.

API areas (per backend module ownership):
  /api/auth/...          apps.accounts
  /api/patients/...      apps.patients
  /api/invitations/...   apps.invitations
  /api/medications/...   apps.medications
  /api/checkins/...      apps.checkins
  /api/alerts/...        apps.alerts
  /api/qr/...            apps.qr
  /api/notifications/... apps.notifications
  /api/analytics/...     apps.patients (history/analytics views)
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("apps.accounts.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/invitations/", include("apps.invitations.urls")),
    path("api/medications/", include("apps.medications.urls")),
    path("api/checkins/", include("apps.checkins.urls")),
    path("api/alerts/", include("apps.alerts.urls")),
    path("api/qr/", include("apps.qr.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/analytics/", include("apps.patients.analytics_urls")),

    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
