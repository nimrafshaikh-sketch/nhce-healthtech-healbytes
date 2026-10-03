import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.patients.models import Patient
from apps.documents.models import MedicalDocument
from apps.documents.embeddings import index_document_chunks
from django.core.files.base import ContentFile

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds deterministic demo dataset for hackathon (Phase 2)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting to seed deterministic demo dataset..."))
        
        doctor, _ = User.objects.get_or_create(email="dr.demo@healbytes.local", defaults={
            "username": "dr.demo@healbytes.local",
            "first_name": "Demo", 
            "last_name": "Doctor", 
            "role": "doctor"
        })
        doctor.set_password("demo123")
        doctor.save()
        
        # ---------------------------------------------------------
        # PATIENT 1: High-Risk (Chronic conditions, multiple docs)
        # ---------------------------------------------------------
        p1_user, _ = User.objects.get_or_create(email="patient1@healbytes.local", defaults={
            "username": "patient1@healbytes.local", "first_name": "Marcus", "last_name": "Highrisk", "role": "patient"
        })
        p1_user.set_password("demo123")
        p1_user.save()
        
        p1, _ = Patient.objects.get_or_create(user=p1_user, doctor=doctor, defaults={
            "full_name": "Marcus Highrisk", 
            "date_of_birth": "1960-05-15", "gender": "male"
        })
        
        # P1 Docs
        d1 = MedicalDocument.objects.create(
            patient=p1, uploaded_by=doctor, title="Q1 Lab Report - A1C and Lipid Panel",
            document_type=MedicalDocument.DocumentType.LAB_REPORT,
            extracted_text="Patient presents with elevated A1C at 8.2%. Blood pressure is 150/95. LDL cholesterol is 160 mg/dL. Diagnosis: Uncontrolled Type 2 Diabetes and Hypertension.",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
        )
        d1.file.save('dummy_lab1.txt', ContentFile(b'dummy content'))
        d1.created_at = timezone.now() - datetime.timedelta(days=80)
        d1.save()
        index_document_chunks(d1)
        
        d2 = MedicalDocument.objects.create(
            patient=p1, uploaded_by=doctor, title="Initial Prescription",
            document_type=MedicalDocument.DocumentType.PRESCRIPTION,
            extracted_text="Prescribed Metformin 1000mg twice daily for diabetes. Prescribed Lisinopril 20mg once daily for hypertension.",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
        )
        d2.file.save('dummy_rx1.txt', ContentFile(b'dummy content'))
        d2.created_at = timezone.now() - datetime.timedelta(days=78)
        d2.save()
        index_document_chunks(d2)

        # ---------------------------------------------------------
        # PATIENT 2: Normal (Control)
        # ---------------------------------------------------------
        p2_user, _ = User.objects.get_or_create(email="patient2@healbytes.local", defaults={
            "username": "patient2@healbytes.local", "first_name": "Sarah", "last_name": "Normal", "role": "patient"
        })
        p2_user.set_password("demo123")
        p2_user.save()
        
        p2, _ = Patient.objects.get_or_create(user=p2_user, doctor=doctor, defaults={
            "full_name": "Sarah Normal", 
            "date_of_birth": "1992-08-20", "gender": "female"
        })
        
        d3 = MedicalDocument.objects.create(
            patient=p2, uploaded_by=doctor, title="Annual Physical",
            document_type=MedicalDocument.DocumentType.CONSULTATION,
            extracted_text="Patient in good health. Vitals normal. Blood pressure 110/70. No current medications. Recommended standard daily multivitamin.",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
        )
        d3.file.save('dummy_phys1.txt', ContentFile(b'dummy content'))
        d3.created_at = timezone.now() - datetime.timedelta(days=15)
        d3.save()
        index_document_chunks(d3)

        # ---------------------------------------------------------
        # PATIENT 3: Conflicting/Changed Info (Temporal Reasoning)
        # ---------------------------------------------------------
        p3_user, _ = User.objects.get_or_create(email="patient3@healbytes.local", defaults={
            "username": "patient3@healbytes.local", "first_name": "David", "last_name": "Changed", "role": "patient"
        })
        p3_user.set_password("demo123")
        p3_user.save()
        
        p3, _ = Patient.objects.get_or_create(user=p3_user, doctor=doctor, defaults={
            "full_name": "David Changed", 
            "date_of_birth": "1975-11-05", "gender": "male"
        })
        
        d4 = MedicalDocument.objects.create(
            patient=p3, uploaded_by=doctor, title="Cardiology Consult",
            document_type=MedicalDocument.DocumentType.CONSULTATION,
            extracted_text="Patient experiencing mild angina. Prescribed Amlodipine 5mg once daily.",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
        )
        d4.file.save('dummy_cardio1.txt', ContentFile(b'dummy content'))
        d4.created_at = timezone.now() - datetime.timedelta(days=60)
        d4.save()
        index_document_chunks(d4)
        
        d5 = MedicalDocument.objects.create(
            patient=p3, uploaded_by=doctor, title="Cardiology Follow-up",
            document_type=MedicalDocument.DocumentType.CONSULTATION,
            extracted_text="Patient reported peripheral edema from Amlodipine. Discontinued Amlodipine 5mg. Switched to Losartan 50mg once daily.",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
        )
        d5.file.save('dummy_cardio2.txt', ContentFile(b'dummy content'))
        d5.created_at = timezone.now() - datetime.timedelta(days=10)
        d5.save()
        index_document_chunks(d5)
        
        self.stdout.write(self.style.SUCCESS("Successfully seeded 3 demo patients with medical histories and embeddings!"))
