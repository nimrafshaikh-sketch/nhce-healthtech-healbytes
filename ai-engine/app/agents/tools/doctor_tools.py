"""Doctor Agent tools (Phase 2).

Every tool here is a thin, read-only wrapper around an existing Django
backend endpoint - none of them recompute anything the backend/AI Engine
already computes. They only ever forward the caller's own bearer token
(via `BackendClient`), so the existing authentication and RBAC decide
what each call is actually allowed to see; a doctor who isn't assigned to
a patient gets exactly the same denial (or, for the list endpoints below,
the same empty/absent result) they'd get calling these APIs directly.

Mapping to existing capabilities (see `app/agents/README.md` for the full
table): patient basic info, medications, medication adherence, risk,
longitudinal history, and RAG each already exist somewhere in
`backend/apps/` or the AI Engine's own deterministic pipeline - nothing
here duplicates that logic, it only exposes it to Gemini through a
schema-checked function call.
"""

from __future__ import annotations

from typing import Any

from app.agents.backend_client import BackendClient
from app.agents.tools.base import Tool, ToolContext

_PATIENT_ID_PROPERTY = {
    "patient_id": {
        "type": "string",
        "description": "The ID of the patient, as a string.",
    },
}


# ---------------------------------------------------------------------------
# get_patient_medications
# ---------------------------------------------------------------------------

# Least privilege: drop internal scheduling details (reminder_times,
# reminders_enabled) and redundant patient identity fields (patient,
# patient_name - the caller already supplied patient_id) that the
# backend's MedicationSerializer includes but Gemini doesn't need.
_MEDICATION_ALLOWED_FIELDS = (
    "id", "name", "dosage", "frequency", "instructions",
    "start_date", "end_date", "is_active", "prescribed_by_name",
)


def _get_patient_medications(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    client = BackendClient()
    # Existing endpoint: GET /api/medications/?patient=<id> - for a doctor,
    # already scoped to `patient__doctor=request.user` intersected with
    # this patient_id, so a patient the doctor doesn't own yields an empty
    # list rather than another doctor's medications (see
    # apps.medications.views.MedicationListCreateView.get_queryset).
    data = client.get(
        "/api/medications/",
        bearer_token=context.bearer_token,
        params={"patient": patient_id},
    )
    results = data.get("results", data) if isinstance(data, dict) else data
    medications = [
        {field: med.get(field) for field in _MEDICATION_ALLOWED_FIELDS if field in med}
        for med in (results or [])
    ]
    return {"patient_id": patient_id, "medications": medications, "count": len(medications)}


get_patient_medications = Tool(
    name="get_patient_medications",
    description=(
        "List a patient's medications (name, dosage, frequency, instructions, "
        "active/inactive, prescribing doctor) by patient ID. Only returns "
        "medications the requesting doctor is already authorized to see."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": dict(_PATIENT_ID_PROPERTY),
        "required": ["patient_id"],
    },
    handler=_get_patient_medications,
)


# ---------------------------------------------------------------------------
# get_medication_adherence
# ---------------------------------------------------------------------------


def _get_medication_adherence(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    client = BackendClient()
    # Existing endpoint: GET /api/analytics/patients/{id}/ai-summary/. This
    # is the same call the doctor-facing AI summary screen already makes;
    # it in turn calls the AI Engine's own deterministic
    # compute_medication_adherence (app/history/summary_service.py) - this
    # tool only extracts that one field, it never recomputes adherence
    # itself. See apps.patients.analytics_views.PatientAISummaryView.
    data = client.get(
        f"/api/analytics/patients/{patient_id}/ai-summary/",
        bearer_token=context.bearer_token,
    )
    history = data.get("history") or {}
    adherence = history.get("medication_adherence")
    if adherence is None:
        return {
            "patient_id": patient_id,
            "available": False,
            "message": "No medication adherence data is available for this patient yet.",
        }
    return {"patient_id": patient_id, "available": True, "medication_adherence": adherence}


get_medication_adherence = Tool(
    name="get_medication_adherence",
    description=(
        "Get the existing deterministic medication-adherence assessment "
        "(overall status and per-medication adherence rate, computed by "
        "the AI Engine from reminder logs) for one patient by ID. Does not "
        "recompute adherence - it only reports what the AI Engine already "
        "calculated."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": dict(_PATIENT_ID_PROPERTY),
        "required": ["patient_id"],
    },
    handler=_get_medication_adherence,
)


# ---------------------------------------------------------------------------
# get_patient_risk
# ---------------------------------------------------------------------------

_RISK_FIELD_MAP = {
    "ai_risk_level": "risk_level",
    "ai_risk_score": "risk_score",
    "ai_notes": "reason",
    "ai_recommended_action": "follow_up_action",
    "ai_notification_recipient": "alert_recipient",
    "ai_processed_at": "processed_at",
}


def _get_patient_risk(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    client = BackendClient()
    # Existing endpoint: GET /api/checkins/?patient=<id>. Each check-in
    # already carries the AI Engine's own /analyze result, computed once
    # at submission time by apps.checkins.ai_client.analyze_checkin and
    # stored on the DailyCheckin row - this tool only reads the most
    # recent one, it never calls /analyze itself or recalculates risk.
    data = client.get(
        "/api/checkins/",
        bearer_token=context.bearer_token,
        params={"patient": patient_id},
    )
    results = data.get("results", data) if isinstance(data, dict) else data
    checkins = results or []
    if not checkins:
        return {
            "patient_id": patient_id,
            "available": False,
            "message": "No check-ins recorded for this patient yet.",
        }
    latest = max(checkins, key=lambda c: (c.get("checkin_date") or "", c.get("id") or 0))
    risk = {out_key: latest.get(in_key) for in_key, out_key in _RISK_FIELD_MAP.items()}
    risk["as_of_checkin_date"] = latest.get("checkin_date")
    if not risk.get("risk_level") or risk["risk_level"] in ("pending", "unavailable"):
        return {
            "patient_id": patient_id,
            "available": False,
            "message": (
                f"The most recent check-in ({risk['as_of_checkin_date']}) has no "
                "completed risk assessment yet."
            ),
        }
    return {"patient_id": patient_id, "available": True, "risk": risk}


get_patient_risk = Tool(
    name="get_patient_risk",
    description=(
        "Get the existing deterministic risk assessment (risk level, risk "
        "score, reason, recommended follow-up action, alert recipient) from "
        "a patient's most recent check-in, by patient ID. Does not run a "
        "new risk analysis - it only reports what the AI Engine already "
        "computed for that check-in."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": dict(_PATIENT_ID_PROPERTY),
        "required": ["patient_id"],
    },
    handler=_get_patient_risk,
)


# ---------------------------------------------------------------------------
# get_patient_history
# ---------------------------------------------------------------------------


def _get_patient_history(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    client = BackendClient()
    # Same existing endpoint as get_medication_adherence
    # (GET /api/analytics/patients/{id}/ai-summary/), which bundles the AI
    # Engine's own /history/summary result (checkin_count, symptom/vital
    # trend, latest lab, open follow-up) under "history" - this tool
    # reports that longitudinal summary, minus medication_adherence
    # (its own dedicated tool, kept out here to avoid returning the same
    # data from two different tools).
    data = client.get(
        f"/api/analytics/patients/{patient_id}/ai-summary/",
        bearer_token=context.bearer_token,
    )
    history = dict(data.get("history") or {})
    history.pop("medication_adherence", None)
    if not history:
        return {
            "patient_id": patient_id,
            "available": False,
            "message": "No longitudinal history summary is available for this patient yet.",
        }
    return {"patient_id": patient_id, "available": True, "history": history}


get_patient_history = Tool(
    name="get_patient_history",
    description=(
        "Get the existing deterministic longitudinal history summary for a "
        "patient by ID: check-in count, days since last check-in, "
        "symptom/vital trend direction, most recent lab result, and next "
        "open follow-up appointment. Computed by the AI Engine from the "
        "patient's real records; this tool only reports it."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": dict(_PATIENT_ID_PROPERTY),
        "required": ["patient_id"],
    },
    handler=_get_patient_history,
)


# ---------------------------------------------------------------------------
# search_patient_records (RAG)
# ---------------------------------------------------------------------------


def _search_patient_records(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    query = arguments["query"]
    client = BackendClient()
    # Existing endpoint: GET /api/documents/rag-search/. Reuses the
    # existing patient-scoped retrieval as-is (semantic embedding search,
    # falling back to keyword/TF-cosine - apps.documents.rag /
    # apps.documents.embeddings); this tool adds no new retrieval logic
    # and no new vector store. The backend enforces patient isolation and
    # doctor authorization (including the QR-grant fallback) before any
    # similarity computation runs - see
    # apps.documents.views.DocumentRAGSearchView.
    data = client.get(
        "/api/documents/rag-search/",
        bearer_token=context.bearer_token,
        params={"patient_id": patient_id, "query": query, "top_k": 4},
    )
    results = data.get("results", data) if isinstance(data, dict) else data
    excerpts = results or []
    if not excerpts:
        return {
            "patient_id": patient_id,
            "query": query,
            "available": False,
            "message": "No matching records were found for this patient.",
        }
    return {"patient_id": patient_id, "query": query, "available": True, "excerpts": excerpts}


search_patient_records = Tool(
    name="search_patient_records",
    description=(
        "Search one patient's own clinical documents/records for relevant "
        "excerpts matching a free-text query, using the existing "
        "patient-scoped retrieval (RAG). Only ever searches within the "
        "single patient identified by patient_id, and only if the "
        "requesting doctor is authorized for that patient."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            **_PATIENT_ID_PROPERTY,
            "query": {
                "type": "string",
                "description": "Free-text search query, e.g. a symptom, test name, or medication.",
            },
        },
        "required": ["patient_id", "query"],
    },
    handler=_search_patient_records,
)
