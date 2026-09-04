"""Regression test for real image OCR.

The independent security audit found that "OCR/Vision" was a false claim
for actual images - a real PNG upload produced zero extracted findings
because the pipeline just UTF-8-decoded raw pixel bytes. This test renders
a genuine synthetic lab-report image (drawn text on a blank canvas, saved
as a real PNG - not a fixture of pre-extracted values) and asserts the
API actually runs it through Tesseract OCR and extracts a real biomarker
value from the pixels, end to end through the same upload endpoint used
in production.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor
from apps.patients.models import Patient

try:
    from PIL import Image, ImageDraw, ImageFont

    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PIL_AVAILABLE = False


def _render_lab_report_png() -> bytes:
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
    except OSError:
        font = ImageFont.load_default(size=32)
    img = Image.new("RGB", (750, 240), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((15, 15), "CENTRAL LAB REPORT", fill="black", font=font)
    draw.text((15, 65), "HbA1c: 8.2% (High)", fill="black", font=font)
    draw.text((15, 115), "Fasting Glucose: 165 mg/dL", fill="black", font=font)
    draw.text((15, 165), "Date: 2026-09-04", fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class RealImageOCRTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="OCR Test Patient")

    def test_real_png_photo_of_lab_report_is_actually_ocrd_not_zero_findings(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
        except (ImportError, EnvironmentError, pytesseract.TesseractNotFoundError):
            self.skipTest("Tesseract not installed in environment")
        
        if not _PIL_AVAILABLE:
            self.skipTest("Pillow not installed in this environment")

        png_bytes = _render_lab_report_png()
        resp = self.client.post(
            reverse("document-list-create"),
            data={
                "patient": self.patient.id,
                "title": "Scanned Lab Report Photo",
                "document_type": "LAB_REPORT",
                "file": SimpleUploadedFile("scanned_lab_report.png", png_bytes, content_type="image/png"),
            },
            format="multipart",
            **auth_headers(self.doctor),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["processing_status"], "processed")

        findings = resp.data["extracted_data"].get("clinical_findings", [])
        self.assertGreater(
            len(findings), 0,
            "expected at least one real clinical finding OCR'd from the image pixels, got none - "
            "OCR did not actually run on this image",
        )
        hba1c = next((f for f in findings if f.get("test_name") == "HBA1C"), None)
        self.assertIsNotNone(hba1c, f"expected an HbA1c finding OCR'd from the image, got: {findings}")
        self.assertAlmostEqual(hba1c["numeric_value"], 8.2, delta=0.01)

        # The extracted_text field must contain real OCR output, not empty
        # and not raw undecoded binary pixel garbage.
        self.assertIn("Glucose", resp.data["extracted_text"])
