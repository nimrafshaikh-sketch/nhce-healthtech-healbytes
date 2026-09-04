"""End-to-end tests for the Phase 2 `/api/v1/history/summary` endpoint."""

from tests.factories import valid_history_request_payload


def test_history_summary_valid_payload_returns_200_and_valid_contract(client):
    payload = valid_history_request_payload()

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["patient_id"] == payload["patient_id"]
    assert body["request_id"] == payload["request_id"]
    assert body["generated_at"]
    history = body["history"]
    assert history["checkin_count"] == 2
    assert history["latest_checkin"]["id"] == 2
    assert history["medications"][0]["name"] == "Lisinopril"
    assert history["latest_lab"]["id"] == 20
    assert history["open_follow_up"]["id"] == 30
    # medication_adherence is a new, additive field; the base factory payload
    # supplies no reminder logs, so it must be a safe, non-penalizing "unknown".
    assert history["medication_adherence"]["overall_status"] == "unknown"
    assert history["medication_adherence"]["medications"][0]["status"] == "unknown"


def test_history_summary_rejects_missing_patient_id(client):
    payload = valid_history_request_payload()
    del payload["patient_id"]

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 422
    assert "errors" in response.json()


def test_history_summary_rejects_malformed_checkin(client):
    payload = valid_history_request_payload()
    payload["checkins"][0]["pain_level"] = "very high"  # not an int

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 422


def test_history_summary_handles_empty_history_lists(client):
    payload = valid_history_request_payload()
    payload["checkins"] = []
    payload["medications"] = []
    payload["lab_tests"] = []
    payload["appointments"] = []

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 200
    history = response.json()["history"]
    assert history["checkin_count"] == 0
    assert history["days_since_last_checkin"] is None
    assert history["latest_checkin"] is None
    assert history["medications"] == []
    assert history["latest_lab"] is None
    assert history["open_follow_up"] is None
    assert history["symptom_trend"]["trend"] == "insufficient_data"


def test_analyze_endpoint_still_works_unaffected_by_history_module(client):
    """Phase 1 regression guard: mounting the Phase 2 router must not change
    `/analyze` behavior."""
    from tests.factories import valid_request_payload

    response = client.post("/api/v1/analyze", json=valid_request_payload())
    assert response.status_code == 200


# --- medication_reminder_logs / medication_adherence (additive extension) ----


def test_history_summary_computes_medication_adherence_from_reminder_logs(client):
    payload = valid_history_request_payload()
    # factory's medication id is 10 (Lisinopril)
    payload["medication_reminder_logs"] = [
        {
            "id": 1, "medication_id": 10,
            "scheduled_for": "2026-08-01T08:00:00+00:00",
            "sent_at": "2026-08-01T08:00:05+00:00",
            "acknowledged_at": "2026-08-01T08:10:00+00:00",
        },
        {
            "id": 2, "medication_id": 10,
            "scheduled_for": "2026-08-02T08:00:00+00:00",
            "sent_at": "2026-08-02T08:00:05+00:00",
            "acknowledged_at": None,
        },
    ]

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 200
    adherence = response.json()["history"]["medication_adherence"]
    assert adherence["overall_status"] == "partially_adherent"
    med = adherence["medications"][0]
    assert med["medication_id"] == 10
    assert med["reminders_sent"] == 2
    assert med["reminders_acknowledged"] == 1
    assert med["adherence_rate"] == 0.5


def test_history_summary_rejects_malformed_medication_reminder_log(client):
    payload = valid_history_request_payload()
    payload["medication_reminder_logs"] = [
        {"id": 1, "medication_id": "not-an-int", "scheduled_for": "2026-08-01T08:00:00+00:00",
         "sent_at": "2026-08-01T08:00:05+00:00"}
    ]

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 422


def test_history_summary_omitting_medication_reminder_logs_field_still_works(client):
    """A caller written against the original Phase 2 contract (before this
    field existed) must keep working unmodified."""
    payload = valid_history_request_payload()
    assert "medication_reminder_logs" not in payload

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 200
    assert response.json()["history"]["medication_adherence"]["overall_status"] == "unknown"


# --- Integration-readiness sanity checks --------------------------------------


def test_openapi_schema_includes_all_three_endpoints_and_history_schemas(client):
    """Guards discoverability for other teams: the auto-generated OpenAPI
    spec (what /docs and any codegen tooling consume) must list every route
    and the full Phase 2 + medication-adherence + lab-analysis schema set."""

    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    assert set(spec["paths"].keys()) == {
        "/api/v1/health", "/api/v1/analyze", "/api/v1/history/summary", "/api/v1/lab-analysis",
        "/api/v1/agents/patient-summary", "/api/v1/agents/doctor", "/api/v1/agents/receptionist",
    }

    schemas = spec["components"]["schemas"]
    for name in [
        "PatientHistoryRequest",
        "PatientHistorySummaryResponse",
        "MedicationReminderLogRecord",
        "MedicationAdherenceSummary",
        "MedicationAdherenceDetail",
        "AIAnalysisRequest",
        "AIAnalysisResponse",
        "LabAnalysisRequest",
        "LabAnalysisResponse",
    ]:
        assert name in schemas, f"{name} missing from OpenAPI schema"


def test_history_summary_end_to_end_realistic_payload_all_fields_populated(client):
    """Kitchen-sink integration test: every history list populated at once,
    mirroring what a real backend integration will actually send."""

    payload = {
        "patient_id": "77",
        "request_id": "e2e-full",
        "as_of": "2026-09-04T12:00:00+00:00",
        "checkins": [
            {"id": 1, "checkin_date": "2026-08-30", "symptoms": ["cough"], "mood": "okay",
             "pain_level": 2, "vitals": {"heart_rate": 70, "temperature_c": 36.9},
             "ai_risk_level": "low", "ai_risk_score": 0.15, "created_at": "2026-08-30T08:00:00+00:00"},
            {"id": 2, "checkin_date": "2026-09-02", "symptoms": ["cough", "fever", "fatigue"],
             "mood": "tired", "pain_level": 5, "vitals": {"heart_rate": 82, "temperature_c": 38.1},
             "ai_risk_level": "medium", "ai_risk_score": 0.5, "created_at": "2026-09-02T08:00:00+00:00"},
        ],
        "medications": [
            {"id": 1, "name": "Amoxicillin", "dosage": "500mg", "frequency": "three_times_daily",
             "start_date": "2026-08-28", "end_date": "2026-09-07", "is_active": True},
        ],
        "lab_tests": [
            {"id": 1, "test_name": "CBC", "priority": "urgent", "status": "completed",
             "result_text": "Elevated WBC count.", "result_date": "2026-09-01T10:00:00+00:00",
             "reviewed_at": "2026-09-01T11:00:00+00:00"},
        ],
        "appointments": [
            {"id": 1, "scheduled_at": "2026-09-06T09:00:00+00:00", "status": "confirmed",
             "reason": "Follow-up for fever"},
        ],
        "medication_reminder_logs": [
            {"id": 1, "medication_id": 1, "scheduled_for": "2026-08-29T08:00:00+00:00",
             "sent_at": "2026-08-29T08:00:05+00:00", "acknowledged_at": "2026-08-29T08:15:00+00:00"},
            {"id": 2, "medication_id": 1, "scheduled_for": "2026-08-30T08:00:00+00:00",
             "sent_at": "2026-08-30T08:00:05+00:00", "acknowledged_at": None},
        ],
    }

    response = client.post("/api/v1/history/summary", json=payload)
    assert response.status_code == 200
    history = response.json()["history"]

    assert history["checkin_count"] == 2
    assert history["days_since_last_checkin"] == 2
    assert history["symptom_trend"]["trend"] == "worsening"
    assert history["vital_trend"]["vitals"]["heart_rate"]["trend"] == "increasing"
    assert history["medications"][0]["name"] == "Amoxicillin"
    assert history["latest_lab"]["result_text"] == "Elevated WBC count."
    assert history["open_follow_up"]["id"] == 1
    assert history["medication_adherence"]["overall_status"] == "partially_adherent"
