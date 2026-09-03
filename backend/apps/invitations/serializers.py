from django.utils import timezone
from rest_framework import serializers

from apps.patients.models import Patient
from apps.patients.serializers import PatientCreateSerializer

from .models import InvitationCode


class InvitationCodeSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = InvitationCode
        fields = [
            "id", "code", "doctor", "patient", "patient_name", "expires_at",
            "used_at", "revoked", "is_valid", "is_expired", "created_at",
        ]
        read_only_fields = fields


class InvitationCodeGenerateSerializer(serializers.Serializer):
    """Doctor calls this with either an existing patient id, or inline
    patient+caretaker details to create the draft Patient and invite in one step.

    Receptionist reuses the same flow (per approved scope) but MUST supply
    patient_id for a patient they already created via /api/patients/ - the
    inline patient-creation branch stays doctor-only, since it implicitly
    self-assigns doctor=request.user, which doesn't make sense for a
    receptionist. The invitation's doctor is always patient.doctor, not
    necessarily the caller - so a receptionist generating a code still
    produces an invitation owned by the patient's actual assigned doctor.
    """
    patient_id = serializers.IntegerField(required=False)
    patient = PatientCreateSerializer(required=False)

    def validate(self, attrs):
        if not attrs.get("patient_id") and not attrs.get("patient"):
            raise serializers.ValidationError(
                "Provide either 'patient_id' (existing draft patient) or 'patient' (new patient details)."
            )
        return attrs

    def create(self, validated_data):
        caller = self.context["request"].user

        if validated_data.get("patient_id"):
            patient_qs = Patient.objects.all() if caller.is_receptionist else Patient.objects.filter(doctor=caller)
            try:
                patient = patient_qs.get(id=validated_data["patient_id"])
            except Patient.DoesNotExist:
                raise serializers.ValidationError({"patient_id": "No such patient."})
            if hasattr(patient, "invitation_code") and patient.invitation_code.is_valid:
                raise serializers.ValidationError("This patient already has a valid, unused invitation code.")
        else:
            if caller.is_receptionist:
                raise serializers.ValidationError(
                    "Receptionists must generate invitations for an existing patient (patient_id) - "
                    "create the patient via /api/patients/ first."
                )
            patient_serializer = PatientCreateSerializer(data=validated_data["patient"], context=self.context)
            patient_serializer.is_valid(raise_exception=True)
            patient = patient_serializer.save()

        # The invitation always belongs to the patient's assigned doctor,
        # whether a Doctor or a Receptionist triggered generation.
        doctor = patient.doctor

        # replace any prior (expired/used) code for this patient
        InvitationCode.objects.filter(patient=patient).delete()
        return InvitationCode.objects.create(doctor=doctor, patient=patient)


class InvitationRedeemSerializer(serializers.Serializer):
    """Patient submits the code + sets up their login credentials."""
    code = serializers.CharField(max_length=16)
    email = serializers.EmailField()
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

    def validate_code(self, value):
        value = value.strip().upper()
        try:
            invitation = InvitationCode.objects.select_related("patient").get(code=value)
        except InvitationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid invitation code.")
        if not invitation.is_valid:
            raise serializers.ValidationError("This invitation code has expired, been used, or was revoked.")
        return value


class InvitationRedeemResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    access = serializers.CharField()
    refresh = serializers.CharField()
    patient_id = serializers.IntegerField()
