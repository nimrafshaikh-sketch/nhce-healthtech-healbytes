import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "healbytes.settings")
django.setup()

from apps.accounts.models import User
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.medical_history.models import MedicalHistory
from apps.qr.models import QRAccessGrant
from apps.qr.tokens import generate_qr_token
from rest_framework.test import APIClient

print("Starting End-to-End Workflow Tests...")

# Clear previous test state
QRAccessGrant.objects.all().delete()

# Setup test data
import uuid
def get_doc(email):
    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create_user(username=str(uuid.uuid4())[:15], email=email, role="doctor", password="test")
    return user

doctor_a = get_doc("doc_a@test.com")
doctor_b = get_doc("doc_b@test.com")

patient_a, _ = Patient.objects.get_or_create(full_name="Patient A Test", defaults={"doctor": doctor_a, "phone_number": "1111111111"})
patient_a.doctor = doctor_a
patient_a.save()

patient_b, _ = Patient.objects.get_or_create(full_name="Patient B Test", defaults={"doctor": doctor_b, "phone_number": "2222222222"})
patient_b.doctor = doctor_b
patient_b.save()

# Ensure patient A has history
Appointment.objects.get_or_create(
    patient=patient_a, doctor=doctor_a,
    defaults={"scheduled_at": timezone.now() - timedelta(days=10), "reason": "Fever", "status": "completed"}
)
MedicalHistory.objects.get_or_create(
    patient=patient_a, recorded_by=doctor_a,
    defaults={"diagnosis": "Common Cold", "notes": "Rest and hydration"}
)

client = APIClient()

print("\n--- Test 1: Primary Doctor History Access ---")
client.force_authenticate(user=doctor_a)
res = client.get(f"/api/patients/{patient_a.id}/history/")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert len(res.json()["visits"]) >= 1, "Expected at least 1 visit"
assert len(res.json()["conditions"]) >= 1, "Expected at least 1 condition"
print("PASS: Primary doctor can access history.")

print("\n--- Test 2: Outside Doctor (NO QR Grant) ---")
client.force_authenticate(user=doctor_b)
res = client.get(f"/api/patients/{patient_a.id}/history/")
assert res.status_code == 403, f"Expected 403, got {res.status_code}"
print("PASS: Outside doctor DENIED access without QR.")

print("\n--- Test 3: Generate QR & Tampering ---")
qr_data = generate_qr_token(patient_a)
token = qr_data["token"]
print("QR Generated successfully.")
# Tamper token (just change a character)
tampered = token[:-2] + "xx"
res = client.post("/api/qr/verify/", {"token": tampered})
assert res.status_code == 400, f"Expected 400 for tampered token, got {res.status_code}"
print("PASS: Tampered QR rejected.")

print("\n--- Test 4: Outside Doctor Scans QR ---")
res = client.post("/api/qr/verify/", {"token": token})
assert res.status_code == 200, f"Expected 200 for valid token, got {res.status_code}"
assert QRAccessGrant.has_active_grant(patient=patient_a, doctor=doctor_b), "Grant not created"
print("PASS: QR verified and QRAccessGrant created.")

print("\n--- Test 5: Outside Doctor (WITH QR Grant) ---")
res = client.get(f"/api/patients/{patient_a.id}/history/")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
print("PASS: Outside doctor GRANTED access with QR.")

print("\n--- Test 6: Patient Isolation (Cross-Patient Fetch) ---")
res = client.get(f"/api/patients/{patient_b.id}/history/")
assert res.status_code == 200, f"Expected 200 since doctor B is primary for patient B, got {res.status_code}"

# Try accessing a completely unrelated patient that B is not primary for and has no grant for
unrelated = Patient.objects.exclude(id__in=[patient_a.id, patient_b.id]).first()
if unrelated:
    res = client.get(f"/api/patients/{unrelated.id}/history/")
    assert res.status_code == 403, "Doctor B accessed unrelated patient!"
    print("PASS: Patient isolation enforced.")

print("\n--- Test 7: Expired Grant ---")
grant = QRAccessGrant.objects.filter(patient=patient_a, doctor=doctor_b).first()
grant.expires_at = timezone.now() - timedelta(minutes=1)
grant.save()
res = client.get(f"/api/patients/{patient_a.id}/history/")
assert res.status_code == 403, f"Expected 403 for expired grant, got {res.status_code}"
print("PASS: Expired grant correctly DENIED access.")

print("\nALL TESTS PASSED!")
