"""Medication Intelligence (Phase 3) - deterministic reconciliation.

Reconciles the authoritative `Medication` table (current + historical
records) against document-derived candidate prescriptions extracted from
uploaded `MedicalDocument`s (apps.documents.ocr), and surfaces structured
observations for a doctor to review.

Deliberately NOT LLM-dependent: every check below is a plain, explainable
comparison over real data already in the database - name matching, date-
range overlap, dosage/frequency string comparison, confidence carried over
from the OCR extraction that produced a candidate. No inference is invented
beyond what the underlying records actually say.

HARD RULE: this module never writes to `Medication`. It only reads and
reports. The only path that creates/updates a `Medication` row from a
document is the existing, unchanged `PrescriptionVerifyView` - a doctor's
explicit action. This module adds visibility on top of that flow; it does
not replace or bypass it.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from django.utils import timezone

from apps.documents.models import MedicalDocument
from apps.documents.ocr import KNOWN_DRUGS
from apps.medications.models import Medication

_KNOWN_DRUG_DEFAULTS = {d["name"].lower(): d["standard_dosage"] for d in KNOWN_DRUGS}


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def _medication_summary(med: Medication) -> Dict[str, Any]:
    return {
        "id": med.id,
        "name": med.name,
        "dosage": med.dosage,
        "frequency": med.frequency,
        "start_date": med.start_date.isoformat() if med.start_date else None,
        "end_date": med.end_date.isoformat() if med.end_date else None,
        "is_active": med.is_active,
        "prescribed_by_id": med.prescribed_by_id,
    }


def _candidate_prescriptions(patient_id: int) -> List[Dict[str, Any]]:
    """Document-derived CANDIDATE_PRESCRIPTION findings for this patient,
    with document provenance attached. Reads only `extracted_data`, which
    the existing OCR pipeline already produces - nothing new is extracted
    here."""
    candidates = []
    docs = MedicalDocument.objects.filter(
        patient_id=patient_id,
        document_type=MedicalDocument.DocumentType.PRESCRIPTION,
    ).order_by("-created_at")
    for doc in docs:
        findings = (doc.extracted_data or {}).get("clinical_findings", [])
        for finding in findings:
            if finding.get("entity_type") != "CANDIDATE_PRESCRIPTION":
                continue
            candidates.append({
                **finding,
                "document_id": doc.id,
                "document_title": doc.title,
                "document_extraction_status": doc.extraction_status,
                "document_verified_by_id": doc.verified_by_id,
                "document_created_at": doc.created_at.isoformat(),
            })
    return candidates


def analyze_patient_medications(patient_id: int) -> Dict[str, Any]:
    """Returns current/historical medications plus structured
    reconciliation observations for one patient. Read-only."""
    today = timezone.now().date()

    all_meds = list(Medication.objects.filter(patient_id=patient_id).order_by("-start_date"))
    current_meds = [m for m in all_meds if m.is_active_on(today)]
    historical_meds = [m for m in all_meds if not m.is_active_on(today)]
    candidates = _candidate_prescriptions(patient_id)

    observations: List[Dict[str, Any]] = []

    # --- 1. Duplicate / conflicting active medications ---------------------
    active_by_name: Dict[str, List[Medication]] = {}
    for med in current_meds:
        active_by_name.setdefault(_norm(med.name), []).append(med)

    for norm_name, meds in active_by_name.items():
        if len(meds) < 2:
            continue
        dosages = {m.dosage for m in meds}
        frequencies = {m.frequency for m in meds}
        conflicting = len(dosages) > 1 or len(frequencies) > 1
        observations.append({
            "category": "conflicting_active_medication" if conflicting else "duplicate_active_medication",
            "medication_name": meds[0].name,
            "observation": (
                f"{len(meds)} active medication records for \"{meds[0].name}\" exist simultaneously"
                + (", with differing dosage/frequency between them." if conflicting else ", with matching dosage/frequency.")
            ),
            "evidence": [{"type": "medication_record", "id": m.id, "detail": f"{m.dosage} {m.frequency}"} for m in meds],
            "source": "Structured medication records",
            "confidence": 1.0,  # derived from authoritative DB rows, not extraction
            "requires_clinician_review": True,
        })

    # --- 2. Dosage/frequency change over time (current vs historical) ------
    historical_by_name: Dict[str, List[Medication]] = {}
    for med in historical_meds:
        historical_by_name.setdefault(_norm(med.name), []).append(med)

    for norm_name, current_list in active_by_name.items():
        past = historical_by_name.get(norm_name)
        if not past:
            continue
        latest_current = current_list[0]
        latest_past = max(past, key=lambda m: m.start_date)
        if latest_current.dosage != latest_past.dosage or latest_current.frequency != latest_past.frequency:
            observations.append({
                "category": "medication_regimen_changed_over_time",
                "medication_name": latest_current.name,
                "observation": (
                    f"\"{latest_current.name}\" dosage/frequency changed from "
                    f"{latest_past.dosage} {latest_past.frequency} (record #{latest_past.id}, started {latest_past.start_date}) "
                    f"to {latest_current.dosage} {latest_current.frequency} (record #{latest_current.id}, started {latest_current.start_date})."
                ),
                "evidence": [
                    {"type": "medication_record", "id": latest_past.id, "detail": f"{latest_past.dosage} {latest_past.frequency}"},
                    {"type": "medication_record", "id": latest_current.id, "detail": f"{latest_current.dosage} {latest_current.frequency}"},
                ],
                "source": "Structured medication records (historical vs current)",
                "confidence": 1.0,
                "requires_clinician_review": False,
            })

    # --- 3. Document-derived candidates vs structured records --------------
    for cand in candidates:
        norm_drug = _norm(cand.get("drug_name", ""))
        already_verified = cand.get("is_verified") or cand.get("document_extraction_status") == MedicalDocument.ExtractionStatus.VERIFIED
        matching_current = active_by_name.get(norm_drug)
        matching_historical = historical_by_name.get(norm_drug)

        if matching_current:
            structured = matching_current[0]
            mismatch = structured.dosage != cand.get("dosage") or structured.frequency != cand.get("frequency")
            if mismatch:
                observations.append({
                    "category": "document_structured_discrepancy",
                    "medication_name": cand.get("drug_name"),
                    "observation": (
                        f"Document \"{cand['document_title']}\" describes \"{cand.get('drug_name')}\" as "
                        f"{cand.get('dosage')} {cand.get('frequency')}, but the active structured medication record "
                        f"(#{structured.id}) has {structured.dosage} {structured.frequency}."
                    ),
                    "evidence": [
                        {"type": "document", "id": cand["document_id"], "detail": f"{cand.get('dosage')} {cand.get('frequency')}"},
                        {"type": "medication_record", "id": structured.id, "detail": f"{structured.dosage} {structured.frequency}"},
                    ],
                    "source": f"Document #{cand['document_id']} vs medication record #{structured.id}",
                    "confidence": min(cand.get("confidence", 0.5), 0.95),
                    "requires_clinician_review": True,
                })
        elif not already_verified:
            # Drug mentioned in a document but absent from both current and
            # historical structured records - a real gap, not a fabricated one.
            if not matching_historical:
                observations.append({
                    "category": "undocumented_candidate_medication",
                    "medication_name": cand.get("drug_name"),
                    "observation": (
                        f"Document \"{cand['document_title']}\" mentions \"{cand.get('drug_name')}\" "
                        f"({cand.get('dosage')} {cand.get('frequency')}), which has no corresponding structured "
                        f"medication record for this patient yet."
                    ),
                    "evidence": [{"type": "document", "id": cand["document_id"], "detail": f"{cand.get('dosage')} {cand.get('frequency')}"}],
                    "source": f"Document #{cand['document_id']} (unverified candidate extraction)",
                    "confidence": cand.get("confidence", 0.5),
                    "requires_clinician_review": True,
                })

        # --- 4. Incomplete/uncertain extraction: dosage not explicitly
        # found in the document text, silently defaulted to the drug's
        # standard dosage - flagged so a clinician knows to double-check
        # the source, not just trust the default.
        default_dosage = _KNOWN_DRUG_DEFAULTS.get(norm_drug)
        if not already_verified and default_dosage and cand.get("dosage") == default_dosage:
            observations.append({
                "category": "incomplete_dosage_information",
                "medication_name": cand.get("drug_name"),
                "observation": (
                    f"Document \"{cand['document_title']}\" mentions \"{cand.get('drug_name')}\" but no explicit "
                    f"dosage was found near it in the extracted text; the standard dosage ({default_dosage}) was "
                    f"used as a placeholder. Confirm the actual prescribed dosage before verifying."
                ),
                "evidence": [{"type": "document", "id": cand["document_id"], "detail": "dosage defaulted, not explicitly extracted"}],
                "source": f"Document #{cand['document_id']} (unverified candidate extraction)",
                "confidence": 0.4,
                "requires_clinician_review": True,
            })

    return {
        "patient_id": patient_id,
        "generated_at": timezone.now().isoformat(),
        "current_medications": [_medication_summary(m) for m in current_meds],
        "historical_medications": [_medication_summary(m) for m in historical_meds],
        "unverified_document_candidates": [
            {k: v for k, v in c.items() if k != "document_verified_by_id"} for c in candidates
            if not (c.get("is_verified") or c.get("document_extraction_status") == MedicalDocument.ExtractionStatus.VERIFIED)
        ],
        "observations": observations,
    }
