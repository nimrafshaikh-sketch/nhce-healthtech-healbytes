#!/usr/bin/env python
"""
Reset script to wipe trial/demo mock data from the database and ensure
clean staff seed accounts are ready for live demos.
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from apps.accounts.models import User
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.invitations.models import InvitationCode
from apps.documents.models import MedicalDocument, DocumentChunk
from apps.medications.models import Medication, Prescription, MedicationReminderLog
from apps.checkins.models import DailyCheckin
from apps.alerts.models import Alert
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.notifications.models import Notification, EmailNotificationLog
from apps.medical_history.models import MedicalHistory
from apps.qr.models import QRAccessGrant, QRScanLog

def reset_database():
    print("=" * 60)
    print("Resetting HealBytes Database to Clean Demo State")
    print("=" * 60)

    # 1. Delete dependent transactional records
    print("Clearing transactional and clinical records...")
    QRScanLog.objects.all().delete()
    QRAccessGrant.objects.all().delete()
    EmailNotificationLog.objects.all().delete()
    Notification.objects.all().delete()
    DailyCheckin.objects.all().delete()
    Alert.objects.all().delete()
    DocumentChunk.objects.all().delete()
    MedicalDocument.objects.all().delete()
    MedicationReminderLog.objects.all().delete()
    Prescription.objects.all().delete()
    Medication.objects.all().delete()
    LabTestResult.objects.all().delete()
    LabTestRequest.objects.all().delete()
    MedicalHistory.objects.all().delete()
    Appointment.objects.all().delete()
    InvitationCode.objects.all().delete()

    # 2. Delete non-seed users and all trial patients
    print("Clearing trial patients and temporary test users...")
    Patient.objects.all().delete()

    seed_emails = [
        "doctor@healbytes.local",
        "receptionist@healbytes.local",
        "labtech@healbytes.local",
        "patient@healbytes.local",
    ]
    User.objects.exclude(email__in=seed_emails).delete()

    # 3. Create or reset standard seed accounts
    print("Setting up pristine seed staff & patient accounts...")

    # Doctor
    doc, _ = User.objects.get_or_create(
        email="doctor@healbytes.local",
        defaults={"username": "dr_sharma", "first_name": "Sarah", "last_name": "Sharma", "role": User.Role.DOCTOR},
    )
    doc.username = "dr_sharma"
    doc.first_name = "Sarah"
    doc.last_name = "Sharma"
    doc.role = User.Role.DOCTOR
    doc.set_password("DoctorPass123!")
    doc.save()

    # Receptionist
    rec, _ = User.objects.get_or_create(
        email="receptionist@healbytes.local",
        defaults={"username": "priya_receptionist", "first_name": "Priya", "last_name": "Sharma", "role": User.Role.RECEPTIONIST},
    )
    rec.username = "priya_receptionist"
    rec.first_name = "Priya"
    rec.last_name = "Sharma"
    rec.role = User.Role.RECEPTIONIST
    rec.set_password("ReceptionistPass123!")
    rec.save()

    # Lab Tech
    lab, _ = User.objects.get_or_create(
        email="labtech@healbytes.local",
        defaults={"username": "anil_labtech", "first_name": "Anil", "last_name": "Kumar", "role": User.Role.LAB_TECH},
    )
    lab.username = "anil_labtech"
    lab.first_name = "Anil"
    lab.last_name = "Kumar"
    lab.role = User.Role.LAB_TECH
    lab.set_password("LabTechPass123!")
    lab.save()

    # Seed Patient user
    pat_user, _ = User.objects.get_or_create(
        email="patient@healbytes.local",
        defaults={"username": "rahul_verma", "first_name": "Rahul", "last_name": "Verma", "role": User.Role.PATIENT},
    )
    pat_user.username = "rahul_verma"
    pat_user.first_name = "Rahul"
    pat_user.last_name = "Verma"
    pat_user.role = User.Role.PATIENT
    pat_user.set_password("PatientPass123!")
    pat_user.save()

    # Create baseline patient record for Rahul Verma linked to Dr. Sharma
    patient = Patient.objects.create(
        user=pat_user,
        doctor=doc,
        full_name="Rahul Verma",
        date_of_birth="1990-05-15",
        gender="male",
        phone_number="+1-555-0101",
        address="123 Health Ave, Suite 4",
        medical_notes="History of mild seasonal allergies and hypertension.",
        caretaker_name="Sunita Verma",
        caretaker_relationship="Spouse",
        caretaker_phone_number="+1-555-0102",
        caretaker_email="sunita.verma@example.com",
    )

    from django.utils import timezone
    inv = InvitationCode.objects.create(
        patient=patient,
        doctor=doc,
        used_at=timezone.now(),
    )

    print("\n✅ Reset completed successfully!")
    print("-" * 60)
    print("Clean Seed Accounts:")
    print("1. Doctor:       doctor@healbytes.local       / DoctorPass123!")
    print("2. Receptionist: receptionist@healbytes.local / ReceptionistPass123!")
    print("3. Lab Tech:     labtech@healbytes.local      / LabTechPass123!")
    print("4. Patient:      patient@healbytes.local      / PatientPass123!")
    print("-" * 60)

if __name__ == "__main__":
    reset_database()
