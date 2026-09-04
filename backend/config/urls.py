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
  /api/appointments/...  apps.appointments
  /api/labtests/...      apps.labtests
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

def api_root_view(request):
    return JsonResponse({
        "service": "HealBytes Clinical Backend API",
        "status": "online",
        "frontend_url": "http://localhost:5173",
        "swagger_documentation": "http://localhost:8000/api/docs/",
        "redoc_documentation": "http://localhost:8000/api/redoc/",
        "endpoints": {
            "auth": "/api/auth/",
            "patients": "/api/patients/",
            "appointments": "/api/appointments/",
            "checkins": "/api/checkins/",
            "medications": "/api/medications/",
            "documents": "/api/documents/",
            "labtests": "/api/labtests/",
            "alerts": "/api/alerts/",
            "analytics": "/api/analytics/",
            "invitations": "/api/invitations/",
            "qr": "/api/qr/",
            "notifications": "/api/notifications/",
        },
    })

urlpatterns = [
    path("", api_root_view, name="root"),
    path("api/", api_root_view, name="api-root"),
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
    path("api/appointments/", include("apps.appointments.urls")),
    path("api/labtests/", include("apps.labtests.urls")),
    path("api/documents/", include("apps.documents.urls")),

    # OpenAPI schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
