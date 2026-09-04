"""Contract and unit tests for the lab-result analysis endpoint
(`POST /api/v1/lab-analysis`) and the underlying deterministic reference-range
assessment (`app/analysis/lab_reference.py`).
"""

from datetime import datetime, timezone

from app.analysis.lab_reference import assess_lab_result
from app.analysis.risk_engine import MODEL_VERSION
from app.schemas.common import RiskLevel


def _payload(**overrides):
    base = {
        "patient_id": "1",
        "request_id": "lab-result-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_name": "HBA1C",
        "result_text": "HbA1c 8.2%",
    }
    base.update(overrides)
    return base


# --- API contract tests ------------------------------------------------------


def test_lab_analysis_valid_payload_returns_200_and_valid_contract(client):
    response = client.post("/api/v1/lab-analysis", json=_payload())

    assert response.status_code == 200
    body = response.json()

    assert body["request_id"] == "lab-result-1"
    assert body["test_name"] == "HBA1C"
    assert body["numeric_value"] == 8.2
    assert body["unit"] == "%"
    assert body["reference_range"] == "4.0 - 5.6%"
    assert body["status"] == "ELEVATED"
    assert body["risk_level"] in {level.value for level in RiskLevel}
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert body["model_version"] == MODEL_VERSION


def test_lab_analysis_rejects_invalid_payload(client):
    payload = _payload()
    del payload["test_name"]

    response = client.post("/api/v1/lab-analysis", json=payload)

    assert response.status_code == 422


def test_lab_analysis_normal_value_is_low_risk(client):
    response = client.post("/api/v1/lab-analysis", json=_payload(result_text="HbA1c 5.1%"))
    body = response.json()

    assert body["status"] == "NORMAL"
    assert body["risk_level"] == "Low"


def test_lab_analysis_low_value_flagged(client):
    response = client.post(
        "/api/v1/lab-analysis",
        json=_payload(test_name="BLOOD_GLUCOSE", result_text="Fasting glucose 55 mg/dL"),
    )
    body = response.json()

    assert body["status"] == "LOW"
    assert body["risk_level"] == "Medium"


def test_lab_analysis_is_deterministic(client):
    payload = _payload()
    first = client.post("/api/v1/lab-analysis", json=payload).json()
    second = client.post("/api/v1/lab-analysis", json=payload).json()

    assert first["status"] == second["status"]
    assert first["risk_level"] == second["risk_level"]
    assert first["numeric_value"] == second["numeric_value"]
    assert first["explanation"] == second["explanation"]


# --- Deterministic reference-range assessment unit tests --------------------


def test_assess_lab_result_elevated_hba1c():
    result = assess_lab_result("HBA1C", "HbA1c: 8.2%")
    assert result["status"] == "ELEVATED"
    assert result["numeric_value"] == 8.2
    assert result["risk_level"] == RiskLevel.MEDIUM


def test_assess_lab_result_normal_glucose():
    result = assess_lab_result("BLOOD_GLUCOSE", "Fasting glucose 88 mg/dL")
    assert result["status"] == "NORMAL"
    assert result["risk_level"] == RiskLevel.LOW


def test_assess_lab_result_all_eight_test_names_have_a_reference():
    # Matches apps.labtests.models.LabTestRequest.TestName on the backend -
    # every fixed choice must resolve to a real reference range, never a
    # silent "unknown test type".
    test_names = [
        "CBC", "BLOOD_GLUCOSE", "LIPID_PROFILE", "HBA1C",
        "KFT", "LFT", "TFT", "URINALYSIS",
    ]
    for test_name in test_names:
        result = assess_lab_result(test_name, "value pending")
        assert result["reference_range"] is not None, f"{test_name} has no configured reference range"


def test_assess_lab_result_unknown_test_name_does_not_crash():
    result = assess_lab_result("NOT_A_REAL_TEST", "some text")
    assert result["status"] == "UNKNOWN"
    assert result["risk_level"] == RiskLevel.LOW


def test_assess_lab_result_no_numeric_value_falls_back_to_abnormal_keyword():
    result = assess_lab_result("URINALYSIS", "Protein trace, flagged abnormal")
    assert result["status"] == "ELEVATED"
    assert result["numeric_value"] is None
    assert result["risk_level"] == RiskLevel.MEDIUM


def test_assess_lab_result_no_numeric_value_falls_back_to_normal_keyword():
    result = assess_lab_result("URINALYSIS", "All normal, no findings")
    assert result["status"] == "NORMAL"
    assert result["numeric_value"] is None
    assert result["risk_level"] == RiskLevel.LOW


def test_assess_lab_result_no_signal_at_all_is_unknown_not_a_crash():
    result = assess_lab_result("TFT", "pending review")
    assert result["status"] == "UNKNOWN"
    assert result["numeric_value"] is None
