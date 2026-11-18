from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class DoctorAuthTests(APITestCase):
    def test_doctor_register_and_login(self):
        register_url = reverse("register-doctor")
        payload = {
            "email": "doc@example.com", "username": "doc1", "password": "StrongPass123!",
            "first_name": "Jane", "last_name": "Doe", "specialization": "Cardiology",
        }
        resp = self.client.post(register_url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        login_url = reverse("login")
        resp = self.client.post(login_url, {"email": "doc@example.com", "password": "StrongPass123!"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("access", resp.data)
        self.assertEqual(resp.data["user"]["role"], "doctor")

    def test_login_wrong_password_fails(self):
        self.client.post(reverse("register-doctor"), {
            "email": "doc2@example.com", "username": "doc2", "password": "StrongPass123!",
        }, format="json")
        resp = self.client.post(reverse("login"), {"email": "doc2@example.com", "password": "wrong"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_auth(self):
        resp = self.client.get(reverse("me"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_all_four_roles_authenticate_as_themselves(self):
        from apps.core.test_utils import make_doctor, make_lab_tech, make_patient_user, make_receptionist

        users = [
            (make_doctor(email="d-role@example.com", username="drole", password="StrongPass123!"), "doctor"),
            (make_patient_user(email="p-role@example.com", username="prole", password="StrongPass123!"), "patient"),
            (make_receptionist(email="r-role@example.com", username="rrole", password="StrongPass123!"), "receptionist"),
            (make_lab_tech(email="l-role@example.com", username="lrole", password="StrongPass123!"), "lab_tech"),
        ]
        for user, expected_role in users:
            resp = self.client.post(
                reverse("login"),
                {"email": user.email, "password": "StrongPass123!"},
                format="json",
            )
            self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
            self.assertEqual(resp.data["user"]["id"], user.id)
            self.assertEqual(resp.data["user"]["email"], user.email)
            self.assertEqual(resp.data["user"]["role"], expected_role)

    def test_inactive_user_cannot_authenticate(self):
        from apps.core.test_utils import make_doctor

        inactive_doc = make_doctor(email="inactive@example.com", username="inactivedoc", password="StrongPass123!")
        inactive_doc.is_active = False
        inactive_doc.save(update_fields=["is_active"])

        resp = self.client.post(
            reverse("login"),
            {"email": "inactive@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reload_session_validation_and_refresh_token_rotation(self):
        from datetime import timedelta
        from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
        from apps.core.test_utils import make_patient_user

        patient = make_patient_user(email="reload-pt@example.com", username="reloadpt", password="StrongPass123!")
        login_resp = self.client.post(
            reverse("login"),
            {"email": "reload-pt@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        access_token = login_resp.data["access"]
        refresh_token = login_resp.data["refresh"]

        # Verify JWT claims match the exact authenticated patient
        decoded = AccessToken(access_token)
        self.assertEqual(decoded["role"], "patient")
        self.assertEqual(decoded["email"], "reload-pt@example.com")
        self.assertEqual(str(decoded["user_id"]), str(patient.id))

        # Simulate repeated browser reloads calling /api/auth/me/
        for _ in range(3):
            me_resp = self.client.get(
                reverse("me"),
                HTTP_AUTHORIZATION=f"Bearer {access_token}",
            )
            self.assertEqual(me_resp.status_code, status.HTTP_200_OK)
            self.assertEqual(me_resp.data["id"], patient.id)
            self.assertEqual(me_resp.data["role"], "patient")

        # Expired access token is rejected with 401
        expired_access = AccessToken.for_user(patient)
        expired_access.set_exp(lifetime=-timedelta(minutes=5))
        expired_resp = self.client.get(
            reverse("me"),
            HTTP_AUTHORIZATION=f"Bearer {str(expired_access)}",
        )
        self.assertEqual(expired_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # Refresh token renews the session with a valid access token
        refresh_resp = self.client.post(
            reverse("login-refresh"),
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(refresh_resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_resp.data)
        self.assertIn("refresh", refresh_resp.data)
        self.assertNotEqual(refresh_resp.data["refresh"], refresh_token)
        rotated_access = AccessToken(refresh_resp.data["access"])
        self.assertEqual(rotated_access["role"], "patient")
        self.assertEqual(rotated_access["email"], "reload-pt@example.com")
        self.assertEqual(str(rotated_access["user_id"]), str(patient.id))
        renewed_me = self.client.get(
            reverse("me"),
            HTTP_AUTHORIZATION=f"Bearer {refresh_resp.data['access']}",
        )
        self.assertEqual(renewed_me.status_code, status.HTTP_200_OK)
        self.assertEqual(renewed_me.data["id"], patient.id)

        # Invalid or expired refresh token is rejected with 401
        bad_refresh = self.client.post(
            reverse("login-refresh"),
            {"refresh": "invalid.refresh.token"},
            format="json",
        )
        self.assertEqual(bad_refresh.status_code, status.HTTP_401_UNAUTHORIZED)

        expired_refresh = RefreshToken.for_user(patient)
        expired_refresh.set_exp(lifetime=-timedelta(days=1))
        exp_refresh_resp = self.client.post(
            reverse("login-refresh"),
            {"refresh": str(expired_refresh)},
            format="json",
        )
        self.assertEqual(exp_refresh_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token_and_rotated_token_cannot_replay(self):
        from apps.core.test_utils import make_doctor

        make_doctor(email="logout-doc@example.com", username="logoutdoc", password="StrongPass123!")
        login_resp = self.client.post(
            reverse("login"),
            {"email": "logout-doc@example.com", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)
        original_refresh = login_resp.data["refresh"]

        # Rotate once: original refresh token must be blacklisted automatically
        rotate_resp = self.client.post(
            reverse("login-refresh"),
            {"refresh": original_refresh},
            format="json",
        )
        self.assertEqual(rotate_resp.status_code, status.HTTP_200_OK)
        next_refresh = rotate_resp.data["refresh"]

        replay_old = self.client.post(
            reverse("login-refresh"),
            {"refresh": original_refresh},
            format="json",
        )
        self.assertEqual(replay_old.status_code, status.HTTP_401_UNAUTHORIZED)

        # Explicit logout blacklists the active refresh token
        logout_resp = self.client.post(
            reverse("logout"),
            {"refresh": next_refresh},
            format="json",
        )
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)

        # Reusing the logged-out refresh token is rejected
        after_logout = self.client.post(
            reverse("login-refresh"),
            {"refresh": next_refresh},
            format="json",
        )
        self.assertEqual(after_logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_login_and_register_endpoints_enforce_rate_throttling(self):
        from unittest.mock import patch
        from django.core.cache import cache
        from rest_framework.throttling import ScopedRateThrottle

        self.assertIn("auth_login", ScopedRateThrottle.THROTTLE_RATES)
        self.assertIn("auth_register", ScopedRateThrottle.THROTTLE_RATES)
        self.assertIn("auth_refresh", ScopedRateThrottle.THROTTLE_RATES)
        self.assertIn("invitation_redeem", ScopedRateThrottle.THROTTLE_RATES)

        cache.clear()
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"auth_login": "2/minute", "auth_register": "2/minute"}):
            for _ in range(2):
                resp = self.client.post(
                    reverse("login"),
                    {"email": "nobody@example.com", "password": "WrongPassword!1"},
                    format="json",
                )
                self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
            throttled = self.client.post(
                reverse("login"),
                {"email": "nobody@example.com", "password": "WrongPassword!1"},
                format="json",
            )
            self.assertEqual(throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        cache.clear()
