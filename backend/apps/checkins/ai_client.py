"""Client for the separate AI Engine service.

Integration contracts (matches the AI Engine's existing, fixed schemas - see
ai-engine/app/schemas/request.py and response.py, and app/history/schemas.py):

    1. POST {AI_ENGINE_URL}/api/v1/analyze
       Request body (AIAnalysisRequest):
           {
               "patient_id": str,
               "request_id": str,
               "timestamp": ISO datetime,
               "check_in": {
                   "symptoms": [str, ...],
                   "severity": "mild" | "moderate" | "severe",
                   "duration": {"value": int, "unit": "hours"|"days"|"weeks"}
               },
               "medical_context": {
                   "medical_history": [str, ...],
                   "medication_adherence": [
                       {"medication_name": str, "adherence_status": "adherent"|"partially_adherent"|"non_adherent"|"unknown", "last_taken": date|null}
                   ]
               },
               "historical_context": {
                   "previous_checkins": [
                       {"request_id": str, "timestamp": ISO datetime, "severity": "mild"|"moderate"|"severe", "risk_level": "Low"|"Medium"|"High"|null}
                   ]
               }
           }
       Response body (AIAnalysisResponse):
           {
               "risk_level": "Low"|"Medium"|"High",
               "risk_score": float (0-100),
               "reason": str,
               "alert_recipient": "none"|"care_team"|"physician"|"emergency_services",
               "follow_up_action": str|null,
               "explanation": str|null,
               "model_version": str,
               "request_id": str,
               "timestamp": ISO datetime
           }

    2. POST {AI_ENGINE_URL}/api/v1/history/summary
       Request body (PatientHistoryRequest):
           {
               "patient_id": str,
               "request_id": str,
               "as_of": ISO datetime|null,
               "checkins": [...],
               "medications": [...],
               "lab_tests": [...],
               "appointments": [...],
               "medication_reminder_logs": [...]
           }
       Response body (PatientHistorySummaryResponse):
           {
               "request_id": str,
               "timestamp": ISO datetime,
               "history": {
                   "checkin_count": int,
                   "days_since_last_checkin": int|null,
                   "latest_checkin": {...}|null,
                   "symptom_trend": {...},
                   "vital_trend": {...},
                   "medications": [...],
                   "latest_lab": {...}|null,
                   "open_follow_up": {...}|null,
                   "medication_adherence": {...}
               }
           }

Compatibility shims:
  - severity is derived from the self-reported 0-10 pain_level using a
    standard clinical pain-scale banding (0-3 mild, 4-6 moderate, 7-10 severe).
  - duration: a fixed 1-day duration is sent as a documented daily check-in placeholder.
  - analyze_checkin returns normalized internal dictionary:
    {"risk_level": "low"|"medium"|"high"|"unavailable",
     "risk_score": float 0.0-1.0 or None,
     "reason": str, "recommended_action": str, "notification_recipient": str}
"""
import logging
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"Low", "Medium", "High"}

ANALYZE_PATH = "/api/v1/analyze"
HISTORY_SUMMARY_PATH = "/api/v1/history/summary"

UNAVAILABLE_RESULT = {
    "risk_level": "unavailable",
    "risk_score": None,
    "reason": "",
    "recommended_action": "",
    "notification_recipient": "",
}


def _severity_from_pain_level(pain_level) -> str:
    """Map the self-reported 0-10 pain_level to the AI Engine's SeverityLevel
    using a standard clinical pain-scale banding. No pain_level recorded ->
    neutral "moderate" default."""
    if pain_level is None:
        return "moderate"
    if pain_level <= 3:
        return "mild"
    if pain_level <= 6:
        return "moderate"
    return "severe"


def _risk_level_to_ai_schema(risk_level: Optional[str]) -> Optional[str]:
    """Map internal checkin risk level string ("low", "medium", "high")
    to AI Engine RiskLevel enum ("Low", "Medium", "High")."""
    if not risk_level:
        return None
    mapping = {"low": "Low", "medium": "Medium", "high": "High"}
    return mapping.get(risk_level.lower())


def _build_medical_context(patient) -> dict:
    """Build medical_context from patient's stored notes and medications."""
    medical_history = []
    if getattr(patient, "medical_notes", None):
        for line in patient.medical_notes.splitlines():
            cleaned = line.strip()
            if cleaned:
                medical_history.append(cleaned)

    from apps.medications.models import Medication, MedicationReminderLog

    medications_qs = Medication.objects.filter(patient=patient)
    medication_adherence = []

    for med in medications_qs:
        logs = MedicationReminderLog.objects.filter(medication=med)
        sent = logs.count()
        acknowledged = logs.filter(acknowledged_at__isnull=False).count()

        if sent == 0:
            status = "unknown"
        else:
            rate = acknowledged / sent
            if rate >= 0.8:
                status = "adherent"
            elif rate >= 0.5:
                status = "partially_adherent"
            else:
                status = "non_adherent"

        latest_ack = logs.filter(acknowledged_at__isnull=False).order_by("-acknowledged_at").first()
        last_taken = latest_ack.acknowledged_at.date().isoformat() if latest_ack and latest_ack.acknowledged_at else None

        medication_adherence.append({
            "medication_name": med.name,
            "adherence_status": status,
            "last_taken": last_taken,
        })

    return {
        "medical_history": medical_history,
        "medication_adherence": medication_adherence,
    }


def _build_historical_context(checkin) -> dict:
    """Query and serialize previous check-ins for the same patient (bounded to 10)."""
    from apps.checkins.models import DailyCheckin

    prev_checkins = (
        DailyCheckin.objects.filter(patient_id=checkin.patient_id)
        .exclude(id=checkin.id)
        .order_by("-checkin_date", "-created_at")[:10]
    )

    # Convert to chronological order as expected by trend detection heuristics
    chronological = list(reversed(prev_checkins))

    previous_summaries = []
    for prev in chronological:
        created_ts = prev.created_at or timezone.now()
        previous_summaries.append({
            "request_id": str(prev.id),
            "timestamp": created_ts.isoformat(),
            "severity": _severity_from_pain_level(prev.pain_level),
            "risk_level": _risk_level_to_ai_schema(prev.ai_risk_level),
        })

    return {
        "previous_checkins": previous_summaries,
    }


def _build_request_payload(checkin) -> dict:
    """Assemble complete AI analysis payload including checkin, medical context,
    and historical context."""
    patient = getattr(checkin, "patient", None)
    medical_context = _build_medical_context(patient) if patient else {"medical_history": [], "medication_adherence": []}
    historical_context = _build_historical_context(checkin)

    return {
        "patient_id": str(checkin.patient_id),
        "request_id": str(checkin.id),
        "timestamp": timezone.now().isoformat(),
        "check_in": {
            "symptoms": [s for s in checkin.symptoms if isinstance(s, str) and s.strip()],
            "severity": _severity_from_pain_level(checkin.pain_level),
            "duration": {"value": 1, "unit": "days"},
        },
        "medical_context": medical_context,
        "historical_context": historical_context,
    }


def _parse_response(data: dict) -> dict:
    risk_level = data.get("risk_level")
    if risk_level not in VALID_RISK_LEVELS:
        return {**UNAVAILABLE_RESULT, "reason": "AI engine returned an unrecognized risk_level."}

    risk_score_0_100 = data.get("risk_score")
    if isinstance(risk_score_0_100, (int, float)) and not isinstance(risk_score_0_100, bool) and (
        0.0 <= float(risk_score_0_100) <= 100.0
    ):
        risk_score = float(risk_score_0_100) / 100.0
    else:
        risk_score = None

    return {
        "risk_level": risk_level.lower(),
        "risk_score": risk_score,
        "reason": data.get("reason") or "",
        "recommended_action": data.get("follow_up_action") or "",
        "notification_recipient": data.get("alert_recipient") or "",
    }


def analyze_checkin(checkin) -> dict:
    if not settings.AI_ENGINE_URL:
        logger.info("AI_ENGINE_URL not configured; skipping AI analysis for checkin %s", checkin.id)
        return {**UNAVAILABLE_RESULT, "reason": "AI engine not configured."}

    valid_symptoms = [s for s in checkin.symptoms if isinstance(s, str) and s.strip()]
    if not valid_symptoms:
        logger.info("Checkin %s has no symptoms reported; skipping AI analysis.", checkin.id)
        return {**UNAVAILABLE_RESULT, "reason": "No symptoms reported; AI analysis skipped."}

    payload = _build_request_payload(checkin)
    try:
        response = requests.post(
            f"{settings.AI_ENGINE_URL.rstrip('/')}{ANALYZE_PATH}",
            json=payload,
            timeout=settings.AI_ENGINE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return _parse_response(data)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("AI engine call failed for checkin %s: %s", checkin.id, exc)
        return {**UNAVAILABLE_RESULT, "reason": "AI engine call failed."}


def _serialize_patient_history_request(patient, as_of=None) -> dict:
    """Gathers patient history records from database and formats matching
    PatientHistoryRequest schema in ai-engine/app/history/schemas.py."""
    from apps.appointments.models import Appointment
    from apps.checkins.models import DailyCheckin
    from apps.labtests.models import LabTestRequest
    from apps.medications.models import Medication, MedicationReminderLog

    reference_time = as_of or timezone.now()

    # 1. Check-ins
    checkins_data = []
    for c in DailyCheckin.objects.filter(patient=patient).order_by("checkin_date", "created_at"):
        clean_symptoms = [s for s in c.symptoms if isinstance(s, str) and s.strip()]
        clean_vitals = {str(k): float(v) for k, v in (c.vitals or {}).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        checkins_data.append({
            "id": c.id,
            "checkin_date": c.checkin_date.isoformat(),
            "symptoms": clean_symptoms,
            "mood": c.mood or "",
            "pain_level": c.pain_level,
            "vitals": clean_vitals,
            "ai_risk_level": c.ai_risk_level if c.ai_risk_level in {"pending", "low", "medium", "high", "unavailable"} else None,
            "ai_risk_score": c.ai_risk_score,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    # 2. Medications
    medications_data = []
    for m in Medication.objects.filter(patient=patient).order_by("start_date", "id"):
        medications_data.append({
            "id": m.id,
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "start_date": m.start_date.isoformat(),
            "end_date": m.end_date.isoformat() if m.end_date else None,
            "is_active": bool(m.is_active),
        })

    # 3. Lab Tests
    lab_tests_data = []
    for lab in LabTestRequest.objects.filter(patient=patient).select_related("result").order_by("-created_at"):
        res = getattr(lab, "result", None)
        lab_tests_data.append({
            "id": lab.id,
            "test_name": lab.test_name,
            "priority": lab.priority,
            "status": lab.status,
            "result_text": res.result_text if res else None,
            "result_date": res.created_at.isoformat() if res and res.created_at else None,
            "reviewed_at": res.reviewed_at.isoformat() if res and res.reviewed_at else None,
            "created_at": res.created_at.isoformat() if res and res.created_at else None,
        })

    # 4. Appointments
    appointments_data = []
    for apt in Appointment.objects.filter(patient=patient).order_by("scheduled_at"):
        appointments_data.append({
            "id": apt.id,
            "scheduled_at": apt.scheduled_at.isoformat(),
            "status": apt.status,
            "reason": apt.reason or "",
        })

    # 5. Medication Reminder Logs
    reminder_logs_data = []
    for log in MedicationReminderLog.objects.filter(medication__patient=patient).order_by("scheduled_for"):
        reminder_logs_data.append({
            "id": log.id,
            "medication_id": log.medication_id,
            "scheduled_for": log.scheduled_for.isoformat(),
            "sent_at": log.sent_at.isoformat(),
            "acknowledged_at": log.acknowledged_at.isoformat() if log.acknowledged_at else None,
        })

    return {
        "patient_id": str(patient.id),
        "request_id": f"summary_{patient.id}_{int(reference_time.timestamp())}",
        "as_of": reference_time.isoformat(),
        "checkins": checkins_data,
        "medications": medications_data,
        "lab_tests": lab_tests_data,
        "appointments": appointments_data,
        "medication_reminder_logs": reminder_logs_data,
    }


def get_patient_history_summary(patient, as_of=None) -> Optional[dict]:
    """Calls the AI Engine POST /api/v1/history/summary endpoint with the patient's
    full clinical history records.

    Returns the parsed response dictionary or None on connection/service failure.
    """
    if not settings.AI_ENGINE_URL:
        logger.info("AI_ENGINE_URL not configured; skipping AI history summary for patient %s", patient.id)
        return None

    payload = _serialize_patient_history_request(patient, as_of=as_of)
    try:
        response = requests.post(
            f"{settings.AI_ENGINE_URL.rstrip('/')}{HISTORY_SUMMARY_PATH}",
            json=payload,
            timeout=settings.AI_ENGINE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("AI engine history summary call failed for patient %s: %s", patient.id, exc)
        return None
