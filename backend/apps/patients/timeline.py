"""Patient Timeline (Phase 4) - deterministic chronological aggregation.

Builds a single, unified, chronological view of a patient's real records
across the apps that already own them: appointments, medications, lab
requests/results, daily check-ins (with the existing AI Engine's risk
verdict and follow-up recommendation, already stored on DailyCheckin by
apps.checkins), and uploaded medical documents.

This module creates no new source of truth. Every event is read directly
from an existing model and references it by (event_type, source app,
source id) - nothing here is a duplicate or derived record; it's purely a
read-side aggregation for display, exactly like apps.patients.clinical_brief
already is for its own narrower purpose.

Patient.id is the anchor for every event: each event dict carries
`patient_id` explicitly, and every underlying queryset is filtered by the
same `patient` object passed in - there is no code path where an event from
a different patient could enter the list.
"""

from typing import Any, Dict, List

from apps.appointments.models import Appointment
from apps.checkins.models import DailyCheckin
from apps.documents.models import MedicalDocument
from apps.labtests.models import LabTestRequest
from apps.medications.models import Medication


def build_patient_timeline(patient) -> Dict[str, Any]:
    """Returns a chronological (most recent first) list of real clinical
    events for one patient, each tagged with its source record."""
    patient_id = patient.id
    events: List[Dict[str, Any]] = []

    for appt in Appointment.objects.filter(patient=patient).select_related("doctor"):
        doctor_name = appt.doctor.get_full_name() if appt.doctor else None
        events.append({
            "patient_id": patient_id,
            "event_type": "APPOINTMENT",
            "date": appt.scheduled_at.isoformat(),
            "title": f"Appointment with Dr. {doctor_name or 'Unassigned'} ({appt.get_status_display()})",
            "detail": appt.reason or None,
            "status": appt.status,
            "source": {"type": "appointment", "id": appt.id},
        })

    for med in Medication.objects.filter(patient=patient):
        prescriber = med.prescribed_by.get_full_name() if med.prescribed_by else None
        events.append({
            "patient_id": patient_id,
            "event_type": "PRESCRIPTION_STARTED",
            "date": med.start_date.isoformat(),
            "title": f"{med.name} {med.dosage} prescribed ({med.get_frequency_display()})",
            "detail": f"Prescribed by {prescriber}" if prescriber else None,
            "source": {"type": "medication", "id": med.id},
        })
        if med.end_date:
            events.append({
                "patient_id": patient_id,
                "event_type": "PRESCRIPTION_ENDED",
                "date": med.end_date.isoformat(),
                "title": f"{med.name} {med.dosage} discontinued/ended",
                "detail": None,
                "source": {"type": "medication", "id": med.id},
            })

    lab_requests = LabTestRequest.objects.filter(patient=patient).select_related("result", "requested_by")
    for req in lab_requests:
        requester = req.requested_by.get_full_name() if req.requested_by else None
        events.append({
            "patient_id": patient_id,
            "event_type": "LAB_REQUESTED",
            "date": req.created_at.isoformat(),
            "title": f"{req.get_test_name_display()} requested ({req.get_priority_display()})",
            "detail": f"Requested by {requester}" if requester else None,
            "status": req.status,
            "source": {"type": "lab_test_request", "id": req.id},
        })
        result = getattr(req, "result", None)
        if result:
            events.append({
                "patient_id": patient_id,
                "event_type": "LAB_RESULT",
                "date": result.created_at.isoformat(),
                "title": f"{req.get_test_name_display()} result recorded",
                "detail": result.result_text,
                "reviewed": result.reviewed_at is not None,
                "source": {"type": "lab_test_result", "id": result.id},
            })

    for chk in DailyCheckin.objects.filter(patient=patient):
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

        events.append({
            "patient_id": patient_id,
            "event_type": "CHECK_IN",
            "date": chk.created_at.isoformat(),
            "title": f"Daily check-in ({chk.checkin_date.isoformat()})",
            "detail": ", ".join(chk_symptoms) if chk_symptoms else "No symptoms reported",
            "source": {"type": "checkin", "id": chk.id},
        })
        if chk.ai_risk_level not in (DailyCheckin.RiskLevel.PENDING, DailyCheckin.RiskLevel.UNAVAILABLE):
            events.append({
                "patient_id": patient_id,
                "event_type": "AI_RISK_EVALUATION",
                "date": (chk.ai_processed_at or chk.created_at).isoformat(),
                "title": f"AI risk evaluation: {chk.ai_risk_level.title()}",
                "detail": chk.ai_notes or None,
                "source": {"type": "checkin", "id": chk.id},
            })
        if chk.ai_recommended_action:
            events.append({
                "patient_id": patient_id,
                "event_type": "AI_FOLLOWUP_RECOMMENDATION",
                "date": (chk.ai_processed_at or chk.created_at).isoformat(),
                "title": "AI follow-up recommendation",
                "detail": chk.ai_recommended_action,
                "source": {"type": "checkin", "id": chk.id},
            })

    for doc in MedicalDocument.objects.filter(patient=patient):
        events.append({
            "patient_id": patient_id,
            "event_type": "MEDICAL_DOCUMENT_UPLOADED",
            "date": doc.created_at.isoformat(),
            "title": f"{doc.get_document_type_display()} uploaded: {doc.title}",
            "detail": f"Status: {doc.get_processing_status_display()} / {doc.get_extraction_status_display()}",
            "view_url": f"/api/documents/{doc.id}/view/",
            "source": {"type": "medical_document", "id": doc.id},
        })

    events.sort(key=lambda e: e["date"], reverse=True)

    return {
        "patient_id": patient_id,
        "event_count": len(events),
        "events": events,
    }
