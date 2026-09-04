from rest_framework import serializers

from apps.accounts.models import User

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)
    is_linked = serializers.BooleanField(read_only=True)
    risk_level = serializers.SerializerMethodField()
    last_checkin = serializers.SerializerMethodField()
    medication_adherence_pct = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id", "doctor", "doctor_name", "user", "full_name", "date_of_birth",
            "gender", "phone_number", "address", "medical_notes",
            "caretaker_name", "caretaker_relationship", "caretaker_phone_number",
            "caretaker_email", "is_active", "is_linked", "created_at", "updated_at",
            "risk_level", "last_checkin", "medication_adherence_pct",
        ]
        read_only_fields = ["id", "doctor", "user", "is_linked", "created_at", "updated_at", "risk_level", "last_checkin", "medication_adherence_pct"]

    def get_risk_level(self, obj):
        latest = obj.checkins.order_by('-checkin_date', '-created_at').first()
        return latest.ai_risk_level.upper() if latest and latest.ai_risk_level else None

    def get_last_checkin(self, obj):
        latest = obj.checkins.order_by('-checkin_date', '-created_at').first()
        return latest.created_at if latest else None

    def get_medication_adherence_pct(self, obj):
        from apps.medications.models import MedicationReminderLog
        logs = MedicationReminderLog.objects.filter(medication__patient=obj)
        total = logs.count()
        if total == 0:
            return None
        acknowledged = logs.filter(acknowledged_at__isnull=False).count()
        return int((acknowledged / total) * 100)


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


class AdministrativePatientSerializer(serializers.ModelSerializer):
    """Receptionist-facing patient view. Excludes `medical_notes` (clinical
    content) - receptionist is an administrative actor only, per the
    locked role matrix. Everything else on Patient is fair game (contact
    info, caretaker details, assigned doctor, linked-account status).
    """
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)
    is_linked = serializers.BooleanField(read_only=True)
    risk_level = serializers.SerializerMethodField()
    last_checkin = serializers.SerializerMethodField()
    medication_adherence_pct = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id", "doctor", "doctor_name", "user", "full_name", "date_of_birth",
            "gender", "phone_number", "address",
            "caretaker_name", "caretaker_relationship", "caretaker_phone_number",
            "caretaker_email", "is_active", "is_linked", "created_at", "updated_at",
            "risk_level", "last_checkin", "medication_adherence_pct",
        ]
        read_only_fields = ["id", "user", "is_linked", "created_at", "updated_at", "risk_level", "last_checkin", "medication_adherence_pct"]

    def get_risk_level(self, obj):
        latest = obj.checkins.order_by('-checkin_date', '-created_at').first()
        return latest.ai_risk_level.upper() if latest and latest.ai_risk_level else None

    def get_last_checkin(self, obj):
        latest = obj.checkins.order_by('-checkin_date', '-created_at').first()
        return latest.created_at if latest else None

    def get_medication_adherence_pct(self, obj):
        from apps.medications.models import MedicationReminderLog
        logs = MedicationReminderLog.objects.filter(medication__patient=obj)
        total = logs.count()
        if total == 0:
            return None
        acknowledged = logs.filter(acknowledged_at__isnull=False).count()
        return int((acknowledged / total) * 100)


class ReceptionistPatientCreateSerializer(serializers.ModelSerializer):
    """Used by a Receptionist to add a new patient + caretaker details.
    Unlike PatientCreateSerializer (doctor's own self-service add, where
    doctor=request.user is implicit), the receptionist must explicitly pick
    which doctor the patient is assigned to - see apps.patients.views.
    """
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.DOCTOR),
    )

    class Meta:
        model = Patient
        # No medical_notes here either - receptionist is an administrative
        # actor and shouldn't be entering clinical content any more than
        # they can read it back later (AdministrativePatientSerializer).
        fields = [
            "id", "doctor", "full_name", "date_of_birth", "gender", "phone_number", "address",
            "caretaker_name", "caretaker_relationship",
            "caretaker_phone_number", "caretaker_email",
        ]
        read_only_fields = ["id"]
