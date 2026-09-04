"""Longitudinal Clinical Brief & RAG Evidence Synthesizer.

Combines authoritative PostgreSQL records with patient-scoped RAG document evidence
to produce an evidence-grounded, doctor-ready Clinical Brief with source citations.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone

from apps.documents.embeddings import retrieve_patient_context_semantic
from apps.documents.models import MedicalDocument
from apps.documents.rag import retrieve_patient_context
from apps.medications.intelligence import analyze_patient_medications
from apps.medications.models import Medication
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.checkins.models import DailyCheckin
from apps.appointments.models import Appointment
from apps.patients.grounding import verify_clinical_brief_grounding
from apps.patients.timeline import build_patient_timeline


def _retrieve_rag_evidence(patient_id: int, query: str, top_k: int = 4):
    """Phase 2: semantic (embedding) retrieval first, falling back to the
    original keyword/TF-cosine engine - same pattern as
    DocumentRAGSearchView (apps.documents.views), reused here rather than
    duplicated logic, kept intentionally thin so the Clinical Brief and the
    standalone RAG search endpoint can never silently disagree about which
    method ran."""
    results = retrieve_patient_context_semantic(patient_id=patient_id, query=query, top_k=top_k)
    if results is not None:
        return results, "semantic_embedding_lsa"
    results = retrieve_patient_context(patient_id=patient_id, query=query, top_k=top_k)
    for r in results:
        r.setdefault("retrieval_method", "keyword_tf_cosine_fallback")
    return results, "keyword_tf_cosine_fallback"


def build_clinical_brief(patient) -> Dict[str, Any]:
    """Builds a complete, evidence-grounded Clinical Brief for a patient.
    Guarantees strict patient isolation and preserves original document citations.
    """
    patient_id = patient.id

    # 1. Authoritative Active Medications with Prescribing Doctor Attribution
    active_meds = []
    meds_qs = Medication.objects.filter(patient=patient, is_active=True).order_by("-start_date")
    for m in meds_qs:
        doc_name = patient.doctor.get_full_name() if patient.doctor else "Primary Physician"
        active_meds.append({
            "id": m.id,
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency.replace("_", " ").title(),
            "instructions": m.instructions or "As prescribed",
            "start_date": m.start_date.isoformat() if m.start_date else None,
            "prescribed_by": doc_name,
            "source_citation": f"Prescription Record #{m.id} ({doc_name})",
        })

    # 2. Authoritative Lab Results (Database + Extracted Medical Documents)
    lab_points = []  # List of all historical lab measurements for trend detection

    # A. From LabTestRequest / LabTestResult
    lab_requests = LabTestRequest.objects.filter(patient=patient).select_related("result").order_by("-created_at")
    for req in lab_requests:
        res = getattr(req, "result", None)
        if res and res.result_text:
            # Extract numeric biomarker accurately
            num_match = re.search(r"(?:hba1c|glucose|cholesterol|creatinine|hemoglobin|kft|lipid)?[^\d:]*[:=]?\s*(\d{1,3}(?:\.\d{1,2})?)\s*(%|mg/dl)?", res.result_text, re.IGNORECASE)
            num_val = float(num_match.group(1)) if (num_match and num_match.group(1)) else None
            unit = num_match.group(2) if (num_match and num_match.group(2)) else ("%" if req.test_name == "HBA1C" else "")
            
            created_date = res.created_at.strftime("%Y-%m-%d") if res.created_at else req.created_at.strftime("%Y-%m-%d")
            lab_points.append({
                "source_type": "DATABASE_LAB_RESULT",
                "test_name": req.test_name,
                "display_name": req.get_test_name_display(),
                "result_text": res.result_text,
                "numeric_value": num_val,
                "unit": unit,
                "date": created_date,
                "title": f"Lab Order #{req.id} ({req.test_name})",
                "document_id": None,
                "view_url": None,
            })


    # B. From Uploaded Medical Documents (Extracted Findings)
    medical_docs = MedicalDocument.objects.filter(patient=patient).order_by("-created_at")
    doc_sources = []
    for doc in medical_docs:
        doc_date = doc.created_at.strftime("%Y-%m-%d")
        doc_sources.append({
            "id": doc.id,
            "document_id": doc.id,
            "title": doc.title,
            "type": doc.get_document_type_display(),
            "document_type": doc.get_document_type_display(),
            "date": doc_date,
            "status": doc.processing_status,
            "view_url": f"/api/documents/{doc.id}/view/",
        })

        if doc.extracted_data and isinstance(doc.extracted_data, dict):
            findings = doc.extracted_data.get("clinical_findings", [])
            for f in findings:
                if f.get("entity_type") == "LAB_RESULT":
                    lab_points.append({
                        "source_type": "DOCUMENT_LAB_REPORT",
                        "test_name": f.get("test_name", "UNKNOWN"),
                        "display_name": f.get("display_name", f.get("test_name")),
                        "result_text": f.get("value", ""),
                        "numeric_value": f.get("numeric_value"),
                        "unit": f.get("unit", ""),
                        "status": f.get("status", "NORMAL"),
                        "reference_range": f.get("reference_range", ""),
                        "date": f.get("date") or doc_date,
                        "title": doc.title,
                        "document_id": doc.id,
                        "view_url": f"/api/documents/{doc.id}/view/",
                    })

    # 3. Compute Grounded Historical Trends (e.g. HbA1c 7.9% -> 8.2%)
    trends = []
    # Group by test_name
    labs_by_test = {}
    for pt in lab_points:
        tname = pt["test_name"]
        labs_by_test.setdefault(tname, []).append(pt)

    for tname, points in labs_by_test.items():
        # Sort chronologically (oldest to newest)
        valid_points = [p for p in points if p["numeric_value"] is not None]
        valid_points.sort(key=lambda x: str(x["date"]))

        if len(valid_points) >= 2:
            first_pt = valid_points[0]
            latest_pt = valid_points[-1]
            diff = latest_pt["numeric_value"] - first_pt["numeric_value"]
            direction = "increased" if diff > 0 else ("decreased" if diff < 0 else "remained stable")

            trend_sources = []
            if first_pt.get("document_id"):
                trend_sources.append({"title": first_pt["title"], "document_id": first_pt["document_id"], "view_url": first_pt["view_url"]})
            if latest_pt.get("document_id") and latest_pt["document_id"] != first_pt.get("document_id"):
                trend_sources.append({"title": latest_pt["title"], "document_id": latest_pt["document_id"], "view_url": latest_pt["view_url"]})

            trends.append({
                "biomarker": latest_pt["display_name"],
                "trend": "worsening" if (direction == "increased" and "hba1c" in latest_pt["display_name"].lower()) else direction,
                "direction": direction,
                "summary": f"{latest_pt['display_name']} {direction} from {first_pt['numeric_value']}{first_pt['unit']} to {latest_pt['numeric_value']}{latest_pt['unit']} across historical records.",
                "trend_statement": f"{latest_pt['display_name']} {direction} from {first_pt['numeric_value']}{first_pt['unit']} to {latest_pt['numeric_value']}{latest_pt['unit']} across historical records.",
                "first_value": f"{first_pt['numeric_value']}{first_pt['unit']} ({first_pt['date']})",
                "latest_value": f"{latest_pt['numeric_value']}{latest_pt['unit']} ({latest_pt['date']})",
                "points": [
                    {"date": p["date"], "value": p["numeric_value"], "unit": p["unit"], "source": p["title"]}
                    for p in valid_points
                ],
                "sources": trend_sources,
            })

    # 4. Recent Labs Summary
    recent_labs = []
    for tname, points in labs_by_test.items():
        points.sort(key=lambda x: str(x["date"]), reverse=True)
        latest = points[0]
        recent_labs.append({
            "test_name": latest["display_name"],
            "latest_value": latest["result_text"] or f"{latest['numeric_value']}{latest['unit']}",
            "date": latest["date"],
            "status": latest.get("status", "RECORDED"),
            "reference_range": latest.get("reference_range", "Standard reference"),
            "source_title": latest["title"],
            "document_id": latest.get("document_id"),
            "view_url": latest.get("view_url"),
        })

    # 5. Patient-Scoped RAG Evidence Retrieval (Phase 2: semantic embedding
    # retrieval first, keyword/TF-cosine as the explicit fallback)
    rag_excerpts, rag_retrieval_method = _retrieve_rag_evidence(
        patient_id, "HbA1c Glucose Diabetes Medication Blood Pressure Symptoms", top_k=4
    )

    # 6. Recent Clinical Events & Check-ins
    recent_events = []
    for chk in DailyCheckin.objects.filter(patient=patient).order_by("-checkin_date")[:3]:
        chk_symptoms = []
        if isinstance(chk.symptoms, list):
            for s in chk.symptoms:
                if isinstance(s, str) and s.strip():
                    chk_symptoms.append(s.strip())
                elif isinstance(s, dict):
                    name = s.get("name") or s.get("symptom") or s.get("title")
                    if name:
                        chk_symptoms.append(str(name).strip())
        elif isinstance(chk.symptoms, str) and chk.symptoms.strip():
            chk_symptoms = [chk.symptoms.strip()]

        recent_events.append({
            "type": "DAILY_CHECKIN",
            "date": chk.checkin_date.isoformat(),
            "symptoms": ", ".join(chk_symptoms) if chk_symptoms else "None reported",
            "mood": chk.mood,
            "pain_level": chk.pain_level,
            "risk_verdict": chk.ai_risk_level,
            "vitals": chk.vitals,
        })

    # 7. Inferred Current Conditions
    conditions = set()
    if patient.medical_notes:
        conditions.add(patient.medical_notes.strip())
    # Infer standard condition tags from medications/labs if present
    med_names = [m["name"].lower() for m in active_meds]
    if any("metformin" in n or "glipizide" in n or "insulin" in n for n in med_names) or any("hba1c" in l["test_name"].lower() for l in lab_points):
        conditions.add("Type 2 Diabetes Mellitus")
    if any("lisinopril" in n or "amlodipine" in n or "losartan" in n for n in med_names):
        conditions.add("Essential Hypertension")
    if not conditions:
        conditions.add("Under Routine Clinical Monitoring")

    # 7b. Medication Intelligence (Phase 3) - deterministic reconciliation,
    # never modifies Medication records (see apps.medications.intelligence).
    medication_intelligence = analyze_patient_medications(patient_id)

    # 7c. Patient Timeline (Phase 4) - deterministic chronological
    # aggregation over the same real records already used above.
    patient_timeline = build_patient_timeline(patient)

    # 8. Controlled AI Observations & Synthesis Narrative
    ai_observations = []
    if trends:
        for t in trends:
            ai_observations.append(f"AI Observation: {t['trend_statement']}")
    if any(e.get("risk_verdict") in ["medium", "high"] for e in recent_events):
        ai_observations.append("AI Observation: Patient experienced symptoms of clinical interest on recent check-ins.")
    for obs in medication_intelligence["observations"]:
        if obs["requires_clinician_review"]:
            ai_observations.append(f"AI Observation (Medication Intelligence): {obs['observation']}")
    if not ai_observations:
        ai_observations.append("AI Observation: Patient parameters appear stable across recorded observations.")

    # Narrative synthesis
    narrative_parts = [
        f"Patient {patient.full_name} is actively managed for {', '.join(sorted(list(conditions)))}."
    ]
    if active_meds:
        med_strs = [f"{m['name']} {m['dosage']} ({m['prescribed_by']})" for m in active_meds]
        narrative_parts.append(f"Active prescriptions: {', '.join(med_strs)}.")
    if trends:
        trend_strs = [t["trend_statement"] for t in trends]
        narrative_parts.append(" ".join(trend_strs))
    if recent_events:
        last_event = recent_events[0]
        narrative_parts.append(f"Most recent check-in on {last_event['date']} noted: '{last_event['symptoms']}' with risk evaluated as {last_event['risk_verdict']}.")

    narrative = " ".join(narrative_parts)

    # 9. Unified Sources list - every document-derived claim in this brief
    # must be traceable here (active medications' prescription-record
    # citations, lab source documents, RAG excerpt citations, and the
    # source documents behind any medication-intelligence observation).
    sources = []
    for m in active_meds:
        sources.append({"type": "medication_record", "id": m["id"], "citation": m["source_citation"]})
    for lab in recent_labs:
        if lab.get("document_id"):
            sources.append({"type": "document", "id": lab["document_id"], "citation": f"{lab['source_title']} (Doc #{lab['document_id']})", "view_url": lab.get("view_url")})
    for excerpt in rag_excerpts:
        sources.append({
            "type": "document",
            "id": excerpt.get("document_id"),
            "citation": excerpt.get("citation_tag"),
            "view_url": excerpt.get("view_url"),
        })
    for obs in medication_intelligence["observations"]:
        sources.append({"type": "medication_intelligence_observation", "citation": obs["source"], "evidence": obs["evidence"]})

    brief_data = {
        "narrative": narrative,
        "current_conditions": sorted(list(conditions)),
        "active_medications": active_meds,
        "recent_labs": recent_labs,
        "longitudinal_trends": trends,
        "important_trends": trends,
        "recent_clinical_events": recent_events,
        "ai_observations": ai_observations,
        "rag_evidence_excerpts": rag_excerpts,
        "rag_retrieval_method": rag_retrieval_method,
        "source_documents": doc_sources,
        "medication_intelligence": medication_intelligence,
        "patient_timeline": patient_timeline,
        "sources": sources,
    }

    # 10. Safety / Grounding verification (Phase 7) - the mandatory final
    # step before this brief is considered complete. Independently
    # re-checks every cited medication/document id against the database
    # (not just against the brief's own claims) and removes any AI
    # Observation that cannot be traced to a real, present record. See
    # apps.patients.grounding module docstring.
    grounding_report = verify_clinical_brief_grounding(patient, brief_data)
    brief_data["grounding"] = grounding_report
    if grounding_report["unsupported_claims_removed"]:
        brief_data["ai_observations"] = grounding_report["grounded_ai_observations"]

    return {
        "patient_id": patient_id,
        "patient_name": patient.full_name,
        "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "primary_doctor": patient.doctor.get_full_name() if patient.doctor else "Unassigned",
        "generated_at": timezone.now().isoformat(),
        "clinical_brief": brief_data,
    }

