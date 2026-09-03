from django.urls import path

from . import views

urlpatterns = [
    path("", views.InvitationListView.as_view(), name="invitation-list"),
    path("generate/", views.InvitationGenerateView.as_view(), name="invitation-generate"),
    path("<int:pk>/revoke/", views.InvitationRevokeView.as_view(), name="invitation-revoke"),
    path("redeem/", views.InvitationRedeemView.as_view(), name="invitation-redeem"),
]
