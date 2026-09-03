from django.urls import path

from . import views

urlpatterns = [
    path("requests/", views.LabTestRequestListCreateView.as_view(), name="labtest-request-list-create"),
    path("requests/<int:pk>/", views.LabTestRequestDetailView.as_view(), name="labtest-request-detail"),
    path("requests/<int:pk>/claim/", views.LabTestClaimView.as_view(), name="labtest-request-claim"),
    path("requests/<int:pk>/cancel/", views.LabTestCancelView.as_view(), name="labtest-request-cancel"),
    path("requests/<int:pk>/result/", views.LabTestResultCreateView.as_view(), name="labtest-result-create"),
    path("results/<int:pk>/review/", views.LabTestResultReviewView.as_view(), name="labtest-result-review"),
]
