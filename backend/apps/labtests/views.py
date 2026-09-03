from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor, IsLabTech

from .models import LabTestRequest, LabTestResult
from .serializers import (
    LabTestRequestCreateSerializer,
    LabTestRequestSerializer,
    LabTestResultCreateSerializer,
    LabTestResultSerializer,
)

# NOTE: Receptionist has zero access anywhere in this module, per the locked
# role matrix (flat No on lab order/result) - no view here grants them
# anything, deliberately.


@extend_schema_view(
    get=extend_schema(tags=["Lab Tests"], summary="List lab test requests (Doctor: own patients, "
                                                     "Lab Tech: unclaimed queue + their own claimed items)"),
    post=extend_schema(tags=["Lab Tests"], summary="Request a lab test for a patient (Doctor only, own patients)"),
)
class LabTestRequestListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsDoctor()]
        return [permissions.IsAuthenticated(), (IsDoctor | IsLabTech)()]

    def get_serializer_class(self):
        return LabTestRequestCreateSerializer if self.request.method == "POST" else LabTestRequestSerializer

    def get_queryset(self):
        user = self.request.user
        qs = LabTestRequest.objects.select_related("patient", "requested_by", "assigned_lab_tech")
        if user.is_doctor:
            return qs.filter(patient__doctor=user)
        # lab tech: the unclaimed queue, plus whatever they've already claimed
        return qs.filter(Q(status=LabTestRequest.Status.REQUESTED) | Q(assigned_lab_tech=user))

    def perform_create(self, serializer):
        patient = serializer.validated_data["patient"]
        if patient.doctor_id != self.request.user.id:
            raise PermissionDenied("You can only request lab tests for your own patients.")
        serializer.save(requested_by=self.request.user)


@extend_schema(tags=["Lab Tests"], summary="Retrieve a single lab test request")
class LabTestRequestDetailView(generics.RetrieveAPIView):
    serializer_class = LabTestRequestSerializer
    permission_classes = [permissions.IsAuthenticated, (IsDoctor | IsLabTech)]
    queryset = LabTestRequest.objects.select_related("patient", "requested_by", "assigned_lab_tech")

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        allowed = (
            (user.is_doctor and obj.patient.doctor_id == user.id)
            or (user.is_lab_tech and (obj.status == LabTestRequest.Status.REQUESTED
                                       or obj.assigned_lab_tech_id == user.id))
        )
        if not allowed:
            self.permission_denied(self.request, message="You do not have access to this lab test request.")
        return obj


@extend_schema(tags=["Lab Tests"], summary="Lab Tech claims an unassigned request from the queue",
               request=None, responses=LabTestRequestSerializer)
class LabTestClaimView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsLabTech]

    def post(self, request, pk):
        lab_request = get_object_or_404(LabTestRequest, pk=pk)
        if lab_request.status != LabTestRequest.Status.REQUESTED or lab_request.assigned_lab_tech_id:
            return Response({"detail": "This request has already been claimed or is no longer requestable."},
                             status=status.HTTP_400_BAD_REQUEST)
        lab_request.assigned_lab_tech = request.user
        lab_request.status = LabTestRequest.Status.IN_PROGRESS
        lab_request.save(update_fields=["assigned_lab_tech", "status"])
        return Response(LabTestRequestSerializer(lab_request).data)


@extend_schema(tags=["Lab Tests"], summary="Doctor cancels their own patient's lab test request",
               request=None, responses=LabTestRequestSerializer)
class LabTestCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        lab_request = get_object_or_404(LabTestRequest, pk=pk, patient__doctor=request.user)
        if lab_request.status not in (LabTestRequest.Status.REQUESTED, LabTestRequest.Status.IN_PROGRESS):
            return Response({"detail": f"Cannot cancel a request with status '{lab_request.status}'."},
                             status=status.HTTP_400_BAD_REQUEST)
        lab_request.status = LabTestRequest.Status.CANCELLED
        lab_request.save(update_fields=["status"])
        return Response(LabTestRequestSerializer(lab_request).data)


@extend_schema(tags=["Lab Tests"], summary="Lab Tech submits the result for a request they've claimed",
               request=LabTestResultCreateSerializer, responses=LabTestResultSerializer)
class LabTestResultCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsLabTech]

    def post(self, request, pk):
        lab_request = get_object_or_404(LabTestRequest, pk=pk, assigned_lab_tech=request.user)
        if lab_request.status != LabTestRequest.Status.IN_PROGRESS:
            return Response({"detail": f"Cannot submit a result for status '{lab_request.status}'."},
                             status=status.HTTP_400_BAD_REQUEST)
        if hasattr(lab_request, "result"):
            return Response({"detail": "A result has already been recorded for this request."},
                             status=status.HTTP_400_BAD_REQUEST)

        serializer = LabTestResultCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save(request=lab_request, recorded_by=request.user)

        lab_request.status = LabTestRequest.Status.COMPLETED
        lab_request.save(update_fields=["status"])

        return Response(LabTestResultSerializer(result).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Lab Tests"], summary="Doctor marks a lab result as reviewed",
               request=None, responses=LabTestResultSerializer)
class LabTestResultReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        result = get_object_or_404(LabTestResult, pk=pk, request__patient__doctor=request.user)
        result.reviewed_by = request.user
        result.reviewed_at = timezone.now()
        result.save(update_fields=["reviewed_by", "reviewed_at"])
        return Response(LabTestResultSerializer(result).data)
