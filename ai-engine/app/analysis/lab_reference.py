"""Deterministic lab-result reference-range assessment.

Given a lab technician's free-text result for one of the fixed
apps.labtests.models.LabTestRequest.TestName test types, this extracts a
numeric value where possible and classifies it against a known clinical
reference range - the same category of deterministic, explainable logic as
the rest of this AI Engine (app/analysis/risk_engine.py). No ML/LLM anywhere
in this module, consistent with the rest of the engine's architecture.

Reference ranges for HBA1C/BLOOD_GLUCOSE/LIPID_PROFILE/KFT mirror the values
already used by the backend's document-OCR entity extractor
(backend/apps/documents/ocr.py::KNOWN_LAB_PATTERNS) so the two places a lab
value can enter the system (an uploaded/OCR'd document vs. a lab
technician's direct result entry) agree on what "elevated" means for the
same test. CBC/LFT/TFT/URINALYSIS use one representative primary marker
each (Hemoglobin, ALT, TSH, Urine Protein) since those are multi-parameter
panels and this project's fixed test_name list has no per-parameter
breakdown - a reasonable, honestly-scoped MVP increment, not a full panel
parser.
"""

from __future__ import annotations

import re
from typing import Optional, TypedDict

from app.schemas.common import RiskLevel


class LabReference(TypedDict):
    display_name: str
    value_regex: str
    unit: str
    ref_min: float
    ref_max: float
    ref_range_str: str


LAB_REFERENCES: dict[str, LabReference] = {
    "HBA1C": {
        "display_name": "HbA1c (Glycated Hemoglobin)",
        "value_regex": r"(?<![A-Za-z0-9])(\d{1,2}(?:\.\d{1,2})?)\s*%?",
        "unit": "%",
        "ref_min": 4.0,
        "ref_max": 5.6,
        "ref_range_str": "4.0 - 5.6%",
    },
    "BLOOD_GLUCOSE": {
        "display_name": "Fasting Blood Glucose",
        "value_regex": r"(?<![A-Za-z0-9])(\d{2,3}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 70.0,
        "ref_max": 99.0,
        "ref_range_str": "70 - 99 mg/dL",
    },
    "LIPID_PROFILE": {
        "display_name": "Total Cholesterol",
        "value_regex": r"(?<![A-Za-z0-9])(\d{2,3}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 125.0,
        "ref_max": 200.0,
        "ref_range_str": "< 200 mg/dL",
    },
    "KFT": {
        "display_name": "Serum Creatinine (KFT)",
        "value_regex": r"(?<![A-Za-z0-9])(\d{1,2}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 0.7,
        "ref_max": 1.3,
        "ref_range_str": "0.7 - 1.3 mg/dL",
    },
    "CBC": {
        "display_name": "Hemoglobin (CBC)",
        "value_regex": r"(?<![A-Za-z0-9])(\d{1,2}(?:\.\d{1,2})?)\s*(?:g/dl)?",
        "unit": "g/dL",
        "ref_min": 12.0,
        "ref_max": 17.5,
        "ref_range_str": "12.0 - 17.5 g/dL",
    },
    "LFT": {
        "display_name": "ALT (LFT)",
        "value_regex": r"(?<![A-Za-z0-9])(\d{1,3}(?:\.\d{1,2})?)\s*(?:u/l|iu/l)?",
        "unit": "U/L",
        "ref_min": 7.0,
        "ref_max": 56.0,
        "ref_range_str": "7 - 56 U/L",
    },
    "TFT": {
        "display_name": "TSH (TFT)",
        "value_regex": r"(?<![A-Za-z0-9])(\d{1,2}(?:\.\d{1,3})?)\s*(?:miu/l|uiu/ml)?",
        "unit": "mIU/L",
        "ref_min": 0.4,
        "ref_max": 4.0,
        "ref_range_str": "0.4 - 4.0 mIU/L",
    },
    "URINALYSIS": {
        "display_name": "Urine Protein",
        "value_regex": r"(?<![A-Za-z0-9])(\d{1,3}(?:\.\d{1,2})?)\s*(?:mg/dl)?",
        "unit": "mg/dL",
        "ref_min": 0.0,
        "ref_max": 20.0,
        "ref_range_str": "0 - 20 mg/dL",
    },
}

_ABNORMAL_KEYWORDS = re.compile(
    r"\b(abnormal|elevated|high|positive|critical|reactive)\b", re.IGNORECASE
)
_NORMAL_KEYWORDS = re.compile(r"\b(normal|negative|non-?reactive|within\s+range)\b", re.IGNORECASE)


class LabAssessment(TypedDict):
    display_name: str
    numeric_value: Optional[float]
    unit: Optional[str]
    reference_range: Optional[str]
    status: str
    risk_level: RiskLevel
    explanation: str


def _extract_numeric_value(result_text: str, value_regex: str) -> Optional[float]:
    match = re.search(value_regex, result_text, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1))
    except (ValueError, IndexError):
        return None


def _keyword_fallback(reference: LabReference, text: str) -> LabAssessment:
    """Used when no numeric value could be parsed out of the free text -
    reads abnormal/normal language instead of silently discarding the
    result. A lab tech typing "all normal" or "protein trace positive"
    still produces a real classification, not a blank."""
    if _ABNORMAL_KEYWORDS.search(text):
        return {
            "display_name": reference["display_name"],
            "numeric_value": None,
            "unit": reference["unit"],
            "reference_range": reference["ref_range_str"],
            "status": "ELEVATED",
            "risk_level": RiskLevel.MEDIUM,
            "explanation": (
                f"{reference['display_name']}: no numeric value could be parsed from the "
                "reported result, but it was described using abnormal/elevated language - "
                "the reviewing doctor should confirm the exact value."
            ),
        }
    if _NORMAL_KEYWORDS.search(text):
        return {
            "display_name": reference["display_name"],
            "numeric_value": None,
            "unit": reference["unit"],
            "reference_range": reference["ref_range_str"],
            "status": "NORMAL",
            "risk_level": RiskLevel.LOW,
            "explanation": f"{reference['display_name']}: reported as normal/negative.",
        }
    return {
        "display_name": reference["display_name"],
        "numeric_value": None,
        "unit": reference["unit"],
        "reference_range": reference["ref_range_str"],
        "status": "UNKNOWN",
        "risk_level": RiskLevel.LOW,
        "explanation": (
            f"{reference['display_name']}: no numeric value or clear normal/abnormal language "
            "could be parsed from the reported result text - recorded as-is for doctor review."
        ),
    }


def assess_lab_result(test_name: str, result_text: str) -> LabAssessment:
    """Deterministically classify a lab technician's free-text result.

    Numeric tests are matched against a known reference range when a number
    can be parsed out of the text. If no number is found, falls back to a
    keyword-based read on the free text (see `_keyword_fallback`) rather than
    silently producing an empty result.
    """
    text = (result_text or "").strip()
    reference = LAB_REFERENCES.get(test_name)

    if reference is None:
        # Unknown test_name (shouldn't happen given the fixed choice list on
        # the backend model, but never crash on an unexpected value).
        return {
            "display_name": test_name,
            "numeric_value": None,
            "unit": None,
            "reference_range": None,
            "status": "UNKNOWN",
            "risk_level": RiskLevel.LOW,
            "explanation": "No reference range is configured for this test type; result recorded as-is for doctor review.",
        }

    numeric_value = _extract_numeric_value(text, reference["value_regex"])
    if numeric_value is None:
        return _keyword_fallback(reference, text)

    if numeric_value > reference["ref_max"]:
        lab_status = "ELEVATED"
    elif numeric_value < reference["ref_min"]:
        lab_status = "LOW"
    else:
        lab_status = "NORMAL"
    risk_level = RiskLevel.LOW if lab_status == "NORMAL" else RiskLevel.MEDIUM

    return {
        "display_name": reference["display_name"],
        "numeric_value": numeric_value,
        "unit": reference["unit"],
        "reference_range": reference["ref_range_str"],
        "status": lab_status,
        "risk_level": risk_level,
        "explanation": (
            f"{reference['display_name']} result is {numeric_value}{reference['unit']} "
            f"(reference range {reference['ref_range_str']}) - classified {lab_status.lower()} "
            "by deterministic reference-range comparison."
        ),
    }
