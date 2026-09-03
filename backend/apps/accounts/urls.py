from django.urls import path

from . import views

urlpatterns = [
    path("register/doctor/", views.DoctorRegisterView.as_view(), name="register-doctor"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("login/refresh/", views.RefreshView.as_view(), name="login-refresh"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
]
