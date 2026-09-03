from django.urls import path

from . import views

urlpatterns = [
    path("generate/", views.QRGenerateView.as_view(), name="qr-generate"),
    path("verify/", views.QRVerifyView.as_view(), name="qr-verify"),
]
