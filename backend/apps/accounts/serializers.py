from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Doctor, User


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ["specialization", "hospital_name"]


class UserSerializer(serializers.ModelSerializer):
    doctor_profile = DoctorSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "name",
            "role", "phone", "doctor_profile",
            "date_joined",
        ]
        read_only_fields = ["id", "role", "date_joined", "doctor_profile"]


class DoctorRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    specialization = serializers.CharField(write_only=True, required=False)
    hospital_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "password", "name",
            "phone", "specialization", "hospital_name",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        specialization = validated_data.pop("specialization", "")
        hospital_name = validated_data.pop("hospital_name", "")
        
        user = User(role=User.Role.DOCTOR, **validated_data)
        user.set_password(password)
        user.save()
        
        Doctor.objects.create(user=user, specialization=specialization, hospital_name=hospital_name)
        
        return user


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role/user_id claims to the JWT and login response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
