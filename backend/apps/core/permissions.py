from rest_framework.permissions import BasePermission


class IsDoctor(BasePermission):
    """Allows access only to authenticated users with role == 'doctor'."""
    message = "Only doctors can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "doctor"
        )


class IsPatient(BasePermission):
    """Allows access only to authenticated users with role == 'patient'."""
    message = "Only patients can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "patient"
        )


class IsDoctorOfPatient(BasePermission):
    """Object-level check: the requesting doctor must be linked to the target patient."""
    message = "You are not the assigned doctor for this patient."

    def has_object_permission(self, request, view, obj):
        patient = getattr(obj, "patient", obj)
        doctor_id = getattr(patient, "doctor_id", None)
        return doctor_id is not None and doctor_id == request.user.id


class IsSelfPatient(BasePermission):
    """Object-level check: the requesting patient must own the record."""
    message = "You can only access your own records."

    def has_object_permission(self, request, view, obj):
        patient = getattr(obj, "patient", obj)
        user = getattr(patient, "user", patient)
        return user.id == request.user.id
