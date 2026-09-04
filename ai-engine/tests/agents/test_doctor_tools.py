"""Unit tests for the Doctor Agent tools (Phase 2).

Every backend call is mocked (`BackendClient` or `httpx.get`) - these
tests verify each tool's own contract (which endpoint/params it calls,
how it filters fields, and how it behaves when the backend has no data or
denies access), not the real Django backend. RBAC itself is the existing
backend's job and is exercised for real in `test_backend_client.py` and
the Phase 1 live smoke test; here we confirm each tool respects whatever
the backend says.
"""

from unittest.mock import patch

import pytest

from app.agents.exceptions import ToolExecutionError, UnauthorizedError
from app.agents.tools.base import ToolContext
from app.agents.tools.doctor_tools import (
    get_medication_adherence,
    get_patient_history,
    get_patient_medications,
    get_patient_risk,
    search_patient_records,
)


# ---------------------------------------------------------------------------
# get_patient_medications
# ---------------------------------------------------------------------------


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_patient_medications_filters_fields_and_unwraps_pagination(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {
                "id": 5, "patient": 7, "patient_name": "Jane Doe",
                "prescribed_by": 1, "prescribed_by_name": "Dr. Sharma",
                "name": "Metformin", "dosage": "500mg", "frequency": "twice_daily",
                "instructions": "With food", "start_date": "2026-01-01", "end_date": None,
                "reminder_times": ["08:00", "20:00"], "reminders_enabled": True,
                "is_active": True, "created_at": "x", "updated_at": "y",
            }
        ],
    }

    result = get_patient_medications.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["count"] == 1
    med = result["medications"][0]
    assert med == {
        "id": 5, "name": "Metformin", "dosage": "500mg", "frequency": "twice_daily",
        "instructions": "With food", "start_date": "2026-01-01", "end_date": None,
        "is_active": True, "prescribed_by_name": "Dr. Sharma",
    }
    assert "reminder_times" not in med and "patient_name" not in med
    mock_client_cls.return_value.get.assert_called_once_with(
        "/api/medications/", bearer_token="tok", params={"patient": "7"}
    )


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_patient_medications_empty_for_unowned_patient(mock_client_cls):
    # A doctor querying a patient they don't own gets an empty, correctly
    # scoped list from the backend (not another doctor's medications).
    mock_client_cls.return_value.get.return_value = {"results": []}

    result = get_patient_medications.handler({"patient_id": "99"}, ToolContext(bearer_token="tok"))

    assert result == {"patient_id": "99", "medications": [], "count": 0}


# ---------------------------------------------------------------------------
# get_medication_adherence
# ---------------------------------------------------------------------------


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_medication_adherence_extracts_history_field(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {
        "clinical_brief": {"...": "..."},
        "history": {
            "medication_adherence": {
                "overall_status": "partially_adherent",
                "medications": [{"name": "Metformin", "adherence_rate": 0.6, "status": "partially_adherent"}],
            }
        },
    }

    result = get_medication_adherence.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["available"] is True
    assert result["medication_adherence"]["overall_status"] == "partially_adherent"
    mock_client_cls.return_value.get.assert_called_once_with(
        "/api/analytics/patients/7/ai-summary/", bearer_token="tok"
    )


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_medication_adherence_reports_unavailable_when_missing(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {"history": {}}

    result = get_medication_adherence.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["available"] is False
    assert "message" in result


# ---------------------------------------------------------------------------
# get_patient_risk
# ---------------------------------------------------------------------------


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_patient_risk_picks_most_recent_checkin(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {
        "results": [
            {
                "id": 1, "checkin_date": "2026-08-01", "ai_risk_level": "medium",
                "ai_risk_score": 45.0, "ai_notes": "old", "ai_recommended_action": "monitor",
                "ai_notification_recipient": "care_team", "ai_processed_at": "x",
            },
            {
                "id": 2, "checkin_date": "2026-09-01", "ai_risk_level": "high",
                "ai_risk_score": 78.0, "ai_notes": "worsening symptoms",
                "ai_recommended_action": "Prompt physician review is recommended.",
                "ai_notification_recipient": "physician", "ai_processed_at": "y",
            },
        ]
    }

    result = get_patient_risk.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["available"] is True
    assert result["risk"]["risk_level"] == "high"
    assert result["risk"]["risk_score"] == 78.0
    assert result["risk"]["as_of_checkin_date"] == "2026-09-01"


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_patient_risk_no_checkins(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {"results": []}

    result = get_patient_risk.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["available"] is False


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_patient_risk_pending_analysis_reported_as_unavailable(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {
        "results": [{"id": 1, "checkin_date": "2026-09-01", "ai_risk_level": "pending"}]
    }

    result = get_patient_risk.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["available"] is False


# ---------------------------------------------------------------------------
# get_patient_history
# ---------------------------------------------------------------------------


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_get_patient_history_excludes_medication_adherence(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {
        "history": {
            "checkin_count": 5,
            "days_since_last_checkin": 2,
            "symptom_trend": "stable",
            "medication_adherence": {"overall_status": "adherent"},
        }
    }

    result = get_patient_history.handler({"patient_id": "7"}, ToolContext(bearer_token="tok"))

    assert result["available"] is True
    assert "medication_adherence" not in result["history"]
    assert result["history"]["checkin_count"] == 5


# ---------------------------------------------------------------------------
# search_patient_records (RAG)
# ---------------------------------------------------------------------------


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_search_patient_records_forwards_patient_scoped_query(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {
        "patient_id": 7, "query": "hba1c", "retrieval_method": "semantic_embedding_lsa",
        "results": [{"citation_tag": "Doc #3", "excerpt": "HbA1c 7.9%"}],
        "count": 1,
    }

    result = search_patient_records.handler(
        {"patient_id": "7", "query": "hba1c"}, ToolContext(bearer_token="tok")
    )

    assert result["available"] is True
    assert result["excerpts"][0]["citation_tag"] == "Doc #3"
    mock_client_cls.return_value.get.assert_called_once_with(
        "/api/documents/rag-search/",
        bearer_token="tok",
        params={"patient_id": "7", "query": "hba1c", "top_k": 4},
    )


@patch("app.agents.tools.doctor_tools.BackendClient")
def test_search_patient_records_no_matches(mock_client_cls):
    mock_client_cls.return_value.get.return_value = {"results": [], "count": 0}

    result = search_patient_records.handler(
        {"patient_id": "7", "query": "nothing relevant"}, ToolContext(bearer_token="tok")
    )

    assert result["available"] is False


def test_search_patient_records_requires_patient_id_and_query():
    schema = search_patient_records.parameters_json_schema
    assert set(schema["required"]) == {"patient_id", "query"}


# ---------------------------------------------------------------------------
# Cross-cutting: fail-closed with no bearer token, backend denial surfaces
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tool,arguments",
    [
        (get_patient_medications, {"patient_id": "7"}),
        (get_medication_adherence, {"patient_id": "7"}),
        (get_patient_risk, {"patient_id": "7"}),
        (get_patient_history, {"patient_id": "7"}),
        (search_patient_records, {"patient_id": "7", "query": "q"}),
    ],
)
def test_every_doctor_tool_fails_closed_with_no_token(tool, arguments):
    with pytest.raises(UnauthorizedError):
        tool.handler(arguments, ToolContext(bearer_token=None))


@pytest.mark.parametrize(
    "tool,arguments",
    [
        (get_patient_medications, {"patient_id": "999"}),
        (get_medication_adherence, {"patient_id": "999"}),
        (get_patient_risk, {"patient_id": "999"}),
        (get_patient_history, {"patient_id": "999"}),
        (search_patient_records, {"patient_id": "999", "query": "q"}),
    ],
)
def test_every_doctor_tool_surfaces_backend_denial_for_unowned_patient(tool, arguments):
    """Different backend endpoints signal 'not your patient' differently
    (403 for some, 404 for others that avoid enumeration) - either way the
    tool must fail rather than return data. See app/agents/README.md for
    which endpoint uses which pattern."""
    with patch("app.agents.tools.doctor_tools.BackendClient") as mock_client_cls:
        mock_client_cls.return_value.get.side_effect = UnauthorizedError("denied")
        with pytest.raises(UnauthorizedError):
            tool.handler(arguments, ToolContext(bearer_token="tok"))

    with patch("app.agents.tools.doctor_tools.BackendClient") as mock_client_cls:
        mock_client_cls.return_value.get.side_effect = ToolExecutionError("404 not found")
        with pytest.raises(ToolExecutionError):
            tool.handler(arguments, ToolContext(bearer_token="tok"))
