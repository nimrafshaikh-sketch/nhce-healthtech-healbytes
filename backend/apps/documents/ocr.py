"""OCR & Clinical Document Extraction Engine.
Extracts clinical entities (labs, prescriptions, vitals, consultation summaries)
from uploaded medical documents (PDFs, images, text) with provenance and confidence scores.
"""

import io
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Real OCR for image documents (PNG/JPEG scans/photos of lab reports and
# prescriptions), via the Tesseract OCR engine. Both pytesseract and the
# `tesseract` binary are optional at import time so the rest of the
# document pipeline (text/PDF extraction, entity parsing) keeps working
# even in an environment without the OCR system dependency installed -
# image documents simply fall back to yielding no text (never a crash),
# same as before this was added.
try:
    import pytesseract
    from PIL import Image, ImageOps

    _OCR_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when deps are absent
    _OCR_AVAILABLE = False

# Magic-byte signatures for the image formats this app accepts
# (MedicalDocumentUploadSerializer allow-list: .png, .jpg, .jpeg).
_IMAGE_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"\xff\xd8\xff", "JPEG"),
)


def _sniff_image_format(content: bytes) -> Optional[str]:
    """Detects an image by real file signature (magic bytes), not by the
    client-supplied filename/content-type - a mislabeled or spoofed
    extension never fools this."""
    for signature, fmt in _IMAGE_SIGNATURES:
        if content.startswith(signature):
            return fmt
    return None


def _ocr_image_bytes(content: bytes) -> str:
    """Runs real Tesseract OCR on image bytes and returns the extracted
    text. Applies standard OCR preprocessing (grayscale, 2x upscale,
    autocontrast) - well-established to materially improve Tesseract
    accuracy on photographed/scanned documents versus raw pixels."""
    if not _OCR_AVAILABLE:
        logger.warning("Image document uploaded but pytesseract/Pillow/tesseract is not installed; skipping OCR.")
        return ""
    try:
        image = Image.open(io.BytesIO(content))
        gray = ImageOps.grayscale(image)
        upscaled = gray.resize((gray.width * 2, gray.height * 2), Image.LANCZOS)
        contrasted = ImageOps.autocontrast(upscaled)
        return pytesseract.image_to_string(contrasted, config="--psm 6")
    except Exception as exc:
        logger.warning("OCR failed on image document: %s", exc)
        return ""

# Standard clinical biomarkers and their reference norms
KNOWN_LAB_PATTERNS = [
    {
        "test_name": "HBA1C",
        "display_name": "HbA1c (Glycated Hemoglobin)",
        "patterns": [r"hba1c", r"hemoglobin\s+a1c", r"glycated\s+hemoglobin", r"hb\s*a\s*[l1i]{1,3}\s*c"],
        # The 4th alternative (hb a [l1i]{1,3} c) tolerates the specific,
        # reproducible way real OCR (Tesseract) misreads "1" as "l"/"i" or
        # inserts a stray character right after "hba" in "HbA1c" - observed
        # directly against this project's own OCR output ("HbAl1c"), not a
        # theoretical case. It's intentionally narrow (only around the "1c"
        # in this one biomarker abbreviation) so it doesn't loosen matching
        # for anything else.
        "value_regex": r"(?:hba1c|hemoglobin\s+a1c|glycated\s+hemoglobin|hb\s*a\s*[l1i]{1,3}\s*c)[^\d]{0,25}(\d{1,2}(?:\.\d{1,2})?)\s*(?:%|percent)?",
        "unit": "%",
        "ref_min": 4.0,
        "ref_max": 5.6,
        "ref_range_str": "4.0 - 5.6%"
    },
    {
        "test_name": "BLOOD_GLUCOSE",
        "display_name": "Fasting Blood Glucose",
        "patterns": [r"fasting\s+glucose", r"blood\s+glucose", r"fbs", r"glucose"],
        "value_regex": r"(?:fasting\s+glucose|blood\s+glucose|fbs|glucose)[^\d]{0,25}(\d{2,3}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 70.0,
        "ref_max": 99.0,
        "ref_range_str": "70 - 99 mg/dL"
    },
    {
        "test_name": "LIPID_PROFILE",
        "display_name": "Total Cholesterol",
        "patterns": [r"total\s+cholesterol", r"cholesterol", r"lipid\s+profile"],
        "value_regex": r"(?:total\s+cholesterol|cholesterol)[^\d]{0,25}(\d{2,3}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 125.0,
        "ref_max": 200.0,
        "ref_range_str": "< 200 mg/dL"
    },
    {
        "test_name": "KFT",
        "display_name": "Serum Creatinine (KFT)",
        "patterns": [r"creatinine", r"serum\s+creatinine", r"kft"],
        "value_regex": r"(?:creatinine|serum\s+creatinine)[^\d]{0,25}(\d{1,2}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 0.7,
        "ref_max": 1.3,
        "ref_range_str": "0.7 - 1.3 mg/dL"
    }
]

KNOWN_DRUGS = [
    {"name": "Metformin", "standard_dosage": "500mg", "frequency": "twice_daily"},
    {"name": "Lisinopril", "standard_dosage": "10mg", "frequency": "once_daily"},
    {"name": "Amlodipine", "standard_dosage": "5mg", "frequency": "once_daily"},
    {"name": "Atorvastatin", "standard_dosage": "20mg", "frequency": "once_daily"},
    {"name": "Glipizide", "standard_dosage": "5mg", "frequency": "twice_daily"},
    {"name": "Losartan", "standard_dosage": "50mg", "frequency": "once_daily"},
    {"name": "Hydrochlorothiazide", "standard_dosage": "25mg", "frequency": "once_daily"},
]

DATE_PATTERNS = [
    r"\b(\d{4}-\d{2}-\d{2})\b",
    r"\b(\d{2}/\d{2}/\d{4})\b",
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2}),?\s+(\d{4})\b"
]


def sanitize_document_text(text: str) -> str:
    """Sanitizes document text to prevent prompt injection and remove unprintable control characters."""
    if not text:
        return ""
    # Strip potential prompt injection instruction markers
    cleaned = re.sub(r"(?i)(system\s+override|ignore\s+previous\s+instructions|reveal\s+other\s+patient)", "[SANITIZED_PROMPT_INJECTION_ATTEMPT]", text)
    return cleaned.strip()


def extract_text_from_file(file_obj, file_type: str = "") -> str:
    """Extracts raw text from PDF, text, or image files."""
    try:
        file_obj.seek(0)
        content = file_obj.read()

        # Real image (PNG/JPEG): route through actual OCR (Tesseract), not
        # a UTF-8 decode of binary pixel data. Detected by magic bytes, so
        # this fires regardless of what extension/content-type the upload
        # claimed.
        if isinstance(content, bytes) and _sniff_image_format(content):
            return _ocr_image_bytes(content)

        # If text/plain or readable UTF-8
        if isinstance(content, bytes):
            try:
                decoded = content.decode("utf-8", errors="ignore")
                # If it's a PDF, extract printable text streams
                if "%PDF" in decoded[:20]:
                    # Extract text inside PDF stream parentheses (e.g. (Text) Tj or [ (Text) ])
                    text_parts = re.findall(r"\(([^\(\)\\]{2,})\)\s*(?:Tj|'|\")", decoded)
                    if text_parts:
                        return "\n".join(text_parts)
                    # Fallback to general printable tokens
                    printable = re.findall(r"[A-Za-z0-9\.,:\-%/ ]{3,}", decoded)
                    return " ".join(printable)
                return decoded
            except Exception:
                return str(content)
        return str(content)
    except Exception as exc:
        logger.warning("Failed to extract raw text: %s", exc)
        return ""


def extract_document_entities(raw_text: str, document_type: str) -> Dict[str, Any]:
    """Parses extracted document text into structured clinical findings and provenance metadata."""
    cleaned_text = sanitize_document_text(raw_text)
    findings = []
    confidence = 0.90
    needs_review = False
    
    # 1. Extract Document Date if present
    doc_date = None
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, cleaned_text, re.IGNORECASE)
        if match:
            doc_date = match.group(0)
            break

    # 2. Extract Lab Report Entities
    if document_type in ["LAB_REPORT", "OTHER", "CONSULTATION"]:
        for lab_def in KNOWN_LAB_PATTERNS:
            match = re.search(lab_def["value_regex"], cleaned_text, re.IGNORECASE)
            if match:
                val_str = match.group(1)
                try:
                    numeric_val = float(val_str)
                    is_elevated = numeric_val > lab_def["ref_max"]
                    is_low = numeric_val < lab_def["ref_min"]
                    status = "ELEVATED" if is_elevated else ("LOW" if is_low else "NORMAL")
                    
                    findings.append({
                        "entity_type": "LAB_RESULT",
                        "test_name": lab_def["test_name"],
                        "display_name": lab_def["display_name"],
                        "value": f"{numeric_val}{lab_def['unit']}",
                        "numeric_value": numeric_val,
                        "unit": lab_def["unit"],
                        "status": status,
                        "reference_range": lab_def["ref_range_str"],
                        "date": doc_date,
                        "confidence": 0.95,
                    })
                except ValueError:
                    pass

    # 3. Extract Prescription Candidates
    if document_type in ["PRESCRIPTION", "OTHER", "CONSULTATION"]:
        needs_review = True  # Mandatory doctor review for prescriptions
        for drug in KNOWN_DRUGS:
            if re.search(r"\b" + re.escape(drug["name"]) + r"\b", cleaned_text, re.IGNORECASE):
                # Look for explicit dosage in vicinity (e.g. 500 mg)
                dose_match = re.search(re.escape(drug["name"]) + r"[^\d]{0,15}(\d{1,4}\s*(?:mg|mcg|g))", cleaned_text, re.IGNORECASE)
                dosage = dose_match.group(1).replace(" ", "") if dose_match else drug["standard_dosage"]
                
                # Frequency
                freq = drug["frequency"]
                if re.search(r"\b(twice\s+daily|bid|2x\s*daily)\b", cleaned_text, re.IGNORECASE):
                    freq = "twice_daily"
                elif re.search(r"\b(once\s+daily|qd|1x\s*daily)\b", cleaned_text, re.IGNORECASE):
                    freq = "once_daily"

                findings.append({
                    "entity_type": "CANDIDATE_PRESCRIPTION",
                    "drug_name": drug["name"],
                    "dosage": dosage,
                    "frequency": freq,
                    "instructions": "Take with water as directed",
                    "date": doc_date,
                    "confidence": 0.92,
                    "is_verified": False,
                })

    return {
        "extracted_date": doc_date,
        "clinical_findings": findings,
        "confidence": confidence if findings else 0.50,
        "needs_review": needs_review,
    }
