from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)
    is_linked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "doctor", "doctor_name", "user", "full_name", "date_of_birth",
            "gender", "phone_number", "address", "medical_notes",
            "caretaker_name", "caretaker_relationship", "caretaker_phone_number",
            "caretaker_email", "is_active", "is_linked", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "doctor", "user", "is_linked", "created_at", "updated_at"]


class PatientCreateSerializer(serializers.ModelSerializer):
    """Used by a Doctor to add a new patient + caretaker details.
    Does NOT create a User/login - that happens on invitation redemption.
    """

    class Meta:
        model = Patient
        fields = [
            "id", "full_name", "date_of_birth", "gender", "phone_number", "address",
            "medical_notes", "caretaker_name", "caretaker_relationship",
            "caretaker_phone_number", "caretaker_email",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        validated_data["doctor"] = self.context["request"].user
        return super().create(validated_data)
