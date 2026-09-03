from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Doctor

if TYPE_CHECKING:
    from apps.accounts.models import User
else:
    User = get_user_model()


def make_doctor(email="doctor@example.com", **kwargs):
    user = User(
        email=email,
        username=kwargs.pop("username", email.split("@")[0]),
        name=kwargs.pop("name", "Test Doctor"),
        role=User.Role.DOCTOR,
        **kwargs
    )
    user.set_password("StrongPass123!")
    user.save()
    Doctor.objects.get_or_create(user=user)
    return user


def make_patient_user(email="patient@example.com", **kwargs):
    user = User(
        email=email,
        username=kwargs.pop("username", email.split("@")[0]),
        name=kwargs.pop("name", "Test Patient"),
        role=User.Role.PATIENT,
        **kwargs
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


def auth_headers(user):
    token = RefreshToken.for_user(user).access_token
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}
