from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_patient_user
from apps.notifications.services import create_notification


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = make_patient_user()
        self.headers = auth_headers(self.user)
        self.notification = create_notification(
            user=self.user, notification_type="general", title="Hello", body="World",
        )

    def test_list_notifications(self):
        resp = self.client.get(reverse("notification-list"), **self.headers)
        self.assertEqual(resp.data["count"], 1)

    def test_mark_read(self):
        resp = self.client.post(reverse("notification-read", args=[self.notification.id]), **self.headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["is_read"])
