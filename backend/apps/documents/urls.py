from django.urls import path
from apps.documents import views

urlpatterns = [
    path("", views.DocumentListCreateView.as_view(), name="document-list-create"),
    path("upload/", views.DocumentListCreateView.as_view(), name="document-upload"),
    path("rag-search/", views.DocumentRAGSearchView.as_view(), name="document-rag-search"),
    path("<int:pk>/", views.DocumentDetailView.as_view(), name="document-detail"),
    path("<int:pk>/view/", views.DocumentStreamView.as_view(), name="document-view"),
    path("<int:pk>/verify-prescription/", views.PrescriptionVerifyView.as_view(), name="document-verify-prescription"),
]

