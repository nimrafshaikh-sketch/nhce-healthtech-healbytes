# HealBytes AI Engine — Phase 0 Review Package (Post-Correction)

Branch: `feature/ai-engine`. This package reflects the state of the
implementation **after** the Phase 0 contract-quality correction pass. No
implementation changes were made to produce this package.

## 1. Current `ai-engine/` directory tree

(Generated cache directories — `__pycache__/`, `.pytest_cache/` — are omitted; they are gitignored and not part of the implementation.)

````
ai-engine/
├── .env.example
├── README.md
├── pytest.ini
├── requirements-dev.txt
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── config.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── main.py
│   └── schemas/
│       ├── __init__.py
│       ├── common.py
│       ├── request.py
│       └── response.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── factories.py
    ├── test_api.py
    ├── test_request_schema.py
    └── test_response_schema.py
````

## 2. Dependency versions

**Python (review environment):** 3.10.12 — no Python 3.11+ interpreter is
available in this environment (checked: `python3.11`, `python3.12`,
`python3.13` all absent). The project's target is Python 3.11+; this
correction pass introduced no 3.11-only syntax, but **Python 3.11+
verification is still outstanding** and should be run before merge.

**Declared in `requirements.txt` (runtime):**
- fastapi>=0.115,<1.0
- uvicorn[standard]>=0.30,<1.0
- pydantic>=2.7,<3.0

**Declared in `requirements-dev.txt` (adds, for testing):**
- pytest>=8.0,<9.0
- httpx>=0.27,<1.0

**Actually installed in the review environment (resolved versions):**
- fastapi 0.141.1
- starlette 1.6.0 (fastapi dependency)
- uvicorn 0.52.4
- pydantic 2.13.5
- pytest 8.4.2
- httpx 0.28.1

No new dependencies were added during the correction pass. Scikit-learn,
TensorFlow, Keras, Pandas, and NumPy remain uninstalled and unreferenced.

## 3. Test command and result

Command (run from inside `ai-engine/`):

````
python -m pytest -v
````

Result: **41 passed**, 3 warnings, in 0.02s. (Prior to the correction pass, 22 tests existed; 19 tests were added for the new validation rules, none were removed.)

````
tests/test_api.py::test_health_check PASSED
tests/test_api.py::test_analyze_accepts_valid_payload_but_logic_not_implemented PASSED
tests/test_api.py::test_analyze_rejects_invalid_payload PASSED
tests/test_request_schema.py::test_valid_request_is_accepted PASSED
tests/test_request_schema.py::test_missing_required_field_is_rejected PASSED
tests/test_request_schema.py::test_invalid_data_type_is_rejected PASSED
tests/test_request_schema.py::test_invalid_severity_enum_is_rejected PASSED
tests/test_request_schema.py::test_non_positive_duration_value_is_rejected PASSED
tests/test_request_schema.py::test_empty_symptoms_list_is_rejected PASSED
tests/test_request_schema.py::test_nested_medication_adherence_status_is_validated PASSED
tests/test_request_schema.py::test_unexpected_field_is_rejected PASSED
tests/test_request_schema.py::test_request_without_optional_context_uses_defaults PASSED
tests/test_request_schema.py::test_empty_patient_id_is_rejected PASSED
tests/test_request_schema.py::test_empty_request_id_is_rejected PASSED
tests/test_request_schema.py::test_empty_symptom_string_is_rejected PASSED
tests/test_request_schema.py::test_empty_medication_name_is_rejected PASSED
tests/test_request_schema.py::test_empty_medical_history_entry_is_rejected PASSED
tests/test_request_schema.py::test_duration_value_as_numeric_string_is_rejected PASSED
tests/test_request_schema.py::test_duration_value_as_bool_is_rejected PASSED
tests/test_request_schema.py::test_duration_value_as_float_is_rejected PASSED
tests/test_request_schema.py::test_patient_id_as_non_string_is_rejected PASSED
tests/test_response_schema.py::test_valid_response_is_accepted PASSED
tests/test_response_schema.py::test_missing_required_field_is_rejected PASSED
tests/test_response_schema.py::test_invalid_risk_level_is_rejected[low] PASSED
tests/test_response_schema.py::test_invalid_risk_level_is_rejected[URGENT] PASSED
tests/test_response_schema.py::test_invalid_risk_level_is_rejected[] PASSED
tests/test_response_schema.py::test_invalid_risk_score_is_rejected[-1] PASSED
tests/test_response_schema.py::test_invalid_risk_score_is_rejected[100.1] PASSED
tests/test_response_schema.py::test_invalid_risk_score_is_rejected[high] PASSED
tests/test_response_schema.py::test_invalid_alert_recipient_is_rejected PASSED
tests/test_response_schema.py::test_alert_recipient_is_required PASSED
tests/test_response_schema.py::test_alert_recipient_none_is_valid PASSED
tests/test_response_schema.py::test_follow_up_action_may_be_null PASSED
tests/test_response_schema.py::test_follow_up_action_omitted_defaults_to_null_but_present PASSED
tests/test_response_schema.py::test_follow_up_action_with_valid_text_is_accepted PASSED
tests/test_response_schema.py::test_empty_follow_up_action_is_rejected PASSED
tests/test_response_schema.py::test_empty_request_id_is_rejected PASSED
tests/test_response_schema.py::test_empty_reason_is_rejected PASSED
tests/test_response_schema.py::test_empty_model_version_is_rejected PASSED
tests/test_response_schema.py::test_risk_score_as_numeric_string_is_rejected PASSED
tests/test_response_schema.py::test_risk_score_as_bool_is_rejected PASSED

======================== 41 passed, 3 warnings in 0.02s ========================
````

Warnings observed (non-blocking, environment/library deprecation notices only):
- `StarletteDeprecationWarning`: using `httpx` with `starlette.testclient` is deprecated; suggests `httpx2`.
- `DeprecationWarning`: `anyio.abc.BlockingPortal` alias deprecated in favor of `anyio.from_thread.BlockingPortal`.
- `StarletteDeprecationWarning`: `HTTP_422_UNPROCESSABLE_ENTITY` deprecated in favor of `HTTP_422_UNPROCESSABLE_CONTENT` (used in `app/core/exceptions.py`).

## 4. Confirmation: no Phase 1+ logic exists

Inspected all files below: no risk-scoring algorithm, ML model, TensorFlow/Keras code, trend-detection logic, medication-adherence analysis logic, alert-routing logic, follow-up recommendation logic, chatbot/LLM code, or database/backend/frontend logic is present anywhere in `ai-engine/`. `POST /api/v1/analyze` validates the request contract via Pydantic and then unconditionally raises `HTTPException(501)` — it never computes or returns an actual risk assessment. This is unchanged in intent from the original Phase 0 delivery; the correction pass only tightened schema validation and reworded the README's stack framing.

## 5. `ai-engine/app/schemas/common.py`

````python
"""Shared base model, enums, and primitive types used by both the AI request
and response contracts.
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class StrictModel(BaseModel):
    """Base model that rejects unexpected fields, for strict contract validation."""

    model_config = ConfigDict(extra="forbid")


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strict=True)]
"""A string that must be present, non-empty, and not silently coerced from
another type (e.g. a number or boolean). Used for every required or
optional-but-non-blank text field in the contract (IDs, names, free text)."""


class RiskLevel(str, Enum):
    """Standardized risk classification returned by the AI Engine."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SeverityLevel(str, Enum):
    """Self-reported severity of a check-in."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class DurationUnit(str, Enum):
    """Unit for how long a symptom/condition has been present."""

    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class MedicationAdherenceStatus(str, Enum):
    """Adherence classification for a single medication."""

    ADHERENT = "adherent"
    PARTIALLY_ADHERENT = "partially_adherent"
    NON_ADHERENT = "non_adherent"
    UNKNOWN = "unknown"


class AlertRecipient(str, Enum):
    """Who the AI Engine recommends should be notified about this check-in."""

    NONE = "none"
    CARE_TEAM = "care_team"
    PHYSICIAN = "physician"
    EMERGENCY_SERVICES = "emergency_services"
````

## 6. `ai-engine/app/schemas/request.py`

````python
"""AI Engine input contract.

Defines the structured payload the backend must send for a single patient
check-in analysis request. This module only defines and validates the shape
of incoming data — no risk-analysis logic is implemented here.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import Field

from app.schemas.common import (
    DurationUnit,
    MedicationAdherenceStatus,
    NonEmptyStr,
    RiskLevel,
    SeverityLevel,
    StrictModel,
)


class Duration(StrictModel):
    """How long the current symptoms have been present."""

    value: int = Field(..., gt=0, strict=True, description="Must be a real int, not a numeric string or bool")
    unit: DurationUnit


class CheckInData(StrictModel):
    """The patient's current, self-reported check-in."""

    symptoms: List[NonEmptyStr] = Field(..., min_length=1, description="Reported symptom names")
    severity: SeverityLevel
    duration: Duration


class MedicationAdherenceRecord(StrictModel):
    """Adherence status for a single prescribed medication."""

    medication_name: NonEmptyStr
    adherence_status: MedicationAdherenceStatus = MedicationAdherenceStatus.UNKNOWN
    last_taken: Optional[date] = None


class MedicalContext(StrictModel):
    """Background medical information relevant to future risk analysis."""

    medical_history: List[NonEmptyStr] = Field(default_factory=list)
    medication_adherence: List[MedicationAdherenceRecord] = Field(default_factory=list)


class PreviousCheckInSummary(StrictModel):
    """A compact record of a prior check-in, used for future trend detection."""

    request_id: NonEmptyStr
    timestamp: datetime
    severity: SeverityLevel
    risk_level: Optional[RiskLevel] = None


class HistoricalContext(StrictModel):
    """Prior check-ins supplied by the backend for trend analysis."""

    previous_checkins: List[PreviousCheckInSummary] = Field(default_factory=list)


class AIAnalysisRequest(StrictModel):
    """Full request contract sent from the backend to the AI Engine."""

    patient_id: NonEmptyStr
    request_id: NonEmptyStr
    timestamp: datetime

    check_in: CheckInData
    medical_context: MedicalContext = Field(default_factory=MedicalContext)
    historical_context: HistoricalContext = Field(default_factory=HistoricalContext)
````

## 7. `ai-engine/app/schemas/response.py`

````python
"""AI Engine output contract.

Defines the structured, validated response returned by the AI Engine. Actual
risk-scoring logic is not implemented in Phase 0 — this module only defines
and validates the shape of outgoing data.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import AlertRecipient, NonEmptyStr, RiskLevel, StrictModel


class AIAnalysisResponse(StrictModel):
    """Full response contract returned by the AI Engine to the backend.

    Every field below is always present in a serialized response, giving the
    backend a single predictable shape to deserialize. `follow_up_action` is
    the only field allowed to be `null`; every other field is required.
    """

    request_id: NonEmptyStr
    timestamp: datetime

    risk_level: RiskLevel
    risk_score: float = Field(
        ..., ge=0.0, le=100.0, strict=True, description="0-100 scale; higher means more risk"
    )
    reason: NonEmptyStr

    alert_recipient: AlertRecipient
    follow_up_action: Optional[NonEmptyStr] = None

    model_version: NonEmptyStr
````

## 8. `ai-engine/app/api/routes.py`

````python
"""API routes for the AI Engine.

Phase 0 wires the request/response contract end-to-end through FastAPI and
Pydantic, but does not implement any risk-analysis logic.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.request import AIAnalysisRequest
from app.schemas.response import AIAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict:
    """Basic liveness check."""

    return {"status": "ok", "service": settings.app_name}


@router.post("/analyze", response_model=AIAnalysisResponse, tags=["analysis"])
def analyze_checkin(payload: AIAnalysisRequest) -> AIAnalysisResponse:
    """Validate an incoming check-in analysis request.

    The request contract is fully validated by Pydantic before this function
    runs. Risk-analysis logic is implemented in a later phase; this endpoint
    exists in Phase 0 to prove the request/response contract is
    integration-ready end-to-end.
    """

    logger.info(
        "Received valid analysis request %s for patient %s",
        payload.request_id,
        payload.patient_id,
    )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Risk analysis is not implemented yet (Phase 0: contract foundation only).",
    )
````

## 9. `ai-engine/app/main.py`

````python
"""FastAPI application entry point for the HealBytes AI Engine.

This service is Phase 0: it exposes and validates the AI request/response
contract only. No risk-scoring, ML, or backend logic lives here.
"""

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.model_version,
    description=(
        "AI Engine contract foundation for patient check-in analysis. "
        "Phase 0: request/response contract and validation only."
    ),
)

register_exception_handlers(app)
app.include_router(router, prefix=settings.api_prefix)
````

## 10. `ai-engine/app/config.py`

````python
"""Minimal runtime configuration for the AI Engine, read from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "HealBytes AI Engine"
    api_prefix: str = "/api/v1"
    model_version: str = os.getenv("AI_MODEL_VERSION", "0.0.0-unimplemented")
    log_level: str = os.getenv("AI_LOG_LEVEL", "INFO")


settings = Settings()
````

## 11. `ai-engine/app/core/exceptions.py`

````python
"""Centralized exception handling for the AI Engine API."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a clean, consistent error response for request validation failures."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Invalid request payload.", "errors": exc.errors()},
        )
````

## 12. `ai-engine/tests/factories.py`

````python
"""Reusable valid payload builders for contract tests."""

from datetime import datetime, timezone


def valid_request_payload() -> dict:
    """Return a fresh, fully valid AIAnalysisRequest payload dict."""

    now = datetime.now(timezone.utc).isoformat()
    return {
        "patient_id": "patient-001",
        "request_id": "req-001",
        "timestamp": now,
        "check_in": {
            "symptoms": ["headache", "fatigue"],
            "severity": "moderate",
            "duration": {"value": 2, "unit": "days"},
        },
        "medical_context": {
            "medical_history": ["hypertension"],
            "medication_adherence": [
                {"medication_name": "Lisinopril", "adherence_status": "adherent"}
            ],
        },
        "historical_context": {
            "previous_checkins": [
                {
                    "request_id": "req-000",
                    "timestamp": now,
                    "severity": "mild",
                    "risk_level": "Low",
                }
            ]
        },
    }


def valid_response_payload() -> dict:
    """Return a fresh, fully valid AIAnalysisResponse payload dict."""

    return {
        "request_id": "req-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_level": "Medium",
        "risk_score": 42.5,
        "reason": "Symptom severity trending upward.",
        "alert_recipient": "care_team",
        "follow_up_action": "Schedule a nurse call within 24 hours.",
        "model_version": "0.0.0-unimplemented",
    }
````

## 13. `ai-engine/tests/conftest.py`

````python
"""Shared pytest fixtures for AI Engine tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
````

## 14. `ai-engine/tests/test_request_schema.py`

````python
"""Validation tests for the AI Engine request contract."""

import pytest
from pydantic import ValidationError

from app.schemas.request import AIAnalysisRequest
from tests.factories import valid_request_payload


def test_valid_request_is_accepted():
    request = AIAnalysisRequest.model_validate(valid_request_payload())
    assert request.patient_id == "patient-001"
    assert request.check_in.severity == "moderate"


def test_missing_required_field_is_rejected():
    payload = valid_request_payload()
    del payload["patient_id"]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_invalid_data_type_is_rejected():
    payload = valid_request_payload()
    payload["timestamp"] = "not-a-timestamp"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_invalid_severity_enum_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["severity"] = "catastrophic"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_non_positive_duration_value_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = 0
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_symptoms_list_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["symptoms"] = []
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_nested_medication_adherence_status_is_validated():
    payload = valid_request_payload()
    payload["medical_context"]["medication_adherence"][0]["adherence_status"] = "invalid_status"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_unexpected_field_is_rejected():
    payload = valid_request_payload()
    payload["unexpected_field"] = "not allowed"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_request_without_optional_context_uses_defaults():
    payload = valid_request_payload()
    del payload["medical_context"]
    del payload["historical_context"]
    request = AIAnalysisRequest.model_validate(payload)
    assert request.medical_context.medical_history == []
    assert request.historical_context.previous_checkins == []


# --- Non-empty string validation (correction pass) ---------------------------


def test_empty_patient_id_is_rejected():
    payload = valid_request_payload()
    payload["patient_id"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_request_id_is_rejected():
    payload = valid_request_payload()
    payload["request_id"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_symptom_string_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["symptoms"] = ["headache", ""]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_medication_name_is_rejected():
    payload = valid_request_payload()
    payload["medical_context"]["medication_adherence"][0]["medication_name"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_medical_history_entry_is_rejected():
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = [""]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


# --- Strict primitive types: reject coercion, not just wrong values ---------


def test_duration_value_as_numeric_string_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = "2"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_duration_value_as_bool_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = True
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_duration_value_as_float_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = 2.0
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_patient_id_as_non_string_is_rejected():
    payload = valid_request_payload()
    payload["patient_id"] = 12345
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)
````

## 15. `ai-engine/tests/test_response_schema.py`

````python
"""Validation tests for the AI Engine response contract."""

import pytest
from pydantic import ValidationError

from app.schemas.response import AIAnalysisResponse
from tests.factories import valid_response_payload


def test_valid_response_is_accepted():
    response = AIAnalysisResponse.model_validate(valid_response_payload())
    assert response.risk_level == "Medium"


def test_missing_required_field_is_rejected():
    payload = valid_response_payload()
    del payload["risk_level"]
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("invalid_level", ["low", "URGENT", ""])
def test_invalid_risk_level_is_rejected(invalid_level):
    payload = valid_response_payload()
    payload["risk_level"] = invalid_level
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("invalid_score", [-1, 100.1, "high"])
def test_invalid_risk_score_is_rejected(invalid_score):
    payload = valid_response_payload()
    payload["risk_score"] = invalid_score
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_invalid_alert_recipient_is_rejected():
    payload = valid_response_payload()
    payload["alert_recipient"] = "family_member"
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Response contract consistency (correction pass) ------------------------


def test_alert_recipient_is_required():
    payload = valid_response_payload()
    del payload["alert_recipient"]
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_alert_recipient_none_is_valid():
    payload = valid_response_payload()
    payload["alert_recipient"] = "none"
    response = AIAnalysisResponse.model_validate(payload)
    assert response.alert_recipient == "none"


def test_follow_up_action_may_be_null():
    payload = valid_response_payload()
    payload["follow_up_action"] = None
    response = AIAnalysisResponse.model_validate(payload)
    assert response.follow_up_action is None
    # The field is always present in the serialized output, even when null.
    assert "follow_up_action" in response.model_dump()


def test_follow_up_action_omitted_defaults_to_null_but_present():
    payload = valid_response_payload()
    del payload["follow_up_action"]
    response = AIAnalysisResponse.model_validate(payload)
    assert response.follow_up_action is None
    assert "follow_up_action" in response.model_dump()


def test_follow_up_action_with_valid_text_is_accepted():
    payload = valid_response_payload()
    payload["follow_up_action"] = "Schedule a follow-up call within 24 hours."
    response = AIAnalysisResponse.model_validate(payload)
    assert response.follow_up_action == "Schedule a follow-up call within 24 hours."


def test_empty_follow_up_action_is_rejected():
    payload = valid_response_payload()
    payload["follow_up_action"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Non-empty string validation (correction pass) ---------------------------


def test_empty_request_id_is_rejected():
    payload = valid_response_payload()
    payload["request_id"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_empty_reason_is_rejected():
    payload = valid_response_payload()
    payload["reason"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_empty_model_version_is_rejected():
    payload = valid_response_payload()
    payload["model_version"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Strict primitive types: reject coercion, not just wrong values ---------


def test_risk_score_as_numeric_string_is_rejected():
    payload = valid_response_payload()
    payload["risk_score"] = "42.5"
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_risk_score_as_bool_is_rejected():
    payload = valid_response_payload()
    payload["risk_score"] = True
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)
````

## 16. `ai-engine/tests/test_api.py`

````python
"""End-to-end contract tests for the FastAPI application (no risk logic)."""

from tests.factories import valid_request_payload


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_accepts_valid_payload_but_logic_not_implemented(client):
    response = client.post("/api/v1/analyze", json=valid_request_payload())
    assert response.status_code == 501


def test_analyze_rejects_invalid_payload(client):
    payload = valid_request_payload()
    del payload["patient_id"]
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 422
    assert "errors" in response.json()
````

## 17. `ai-engine/requirements.txt`

````text
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<1.0
pydantic>=2.7,<3.0
````

## 18. `ai-engine/requirements-dev.txt`

````text
-r requirements.txt
pytest>=8.0,<9.0
httpx>=0.27,<1.0
````

## 19. `ai-engine/pytest.ini`

````ini
[pytest]
pythonpath = .
testpaths = tests
````

## 20. `ai-engine/README.md`

````markdown
# HealBytes AI Engine — Phase 0: Contract Foundation

Backend-agnostic FastAPI service defining the request/response contract
between the HealBytes backend and the AI Engine. No risk-analysis logic is
implemented yet — this phase only establishes structure, schemas, and
validation.

## Structure

- `app/schemas/` — Pydantic request (`request.py`) and response
  (`response.py`) contracts, plus shared enums (`common.py`).
- `app/api/routes.py` — `/health` and `/analyze` endpoints. `/analyze`
  validates input and returns `501 Not Implemented`.
- `app/core/` — logging setup and centralized validation-error handling.
- `app/config.py` — environment-driven settings.
- `tests/` — schema and API contract tests.

## Request contract (`AIAnalysisRequest`)

- `patient_id`, `request_id`, `timestamp` — request metadata for
  traceability.
- `check_in` — `symptoms`, `severity` (`mild`/`moderate`/`severe`),
  `duration` (value + unit).
- `medical_context` — `medical_history`, `medication_adherence` records.
- `historical_context` — `previous_checkins` summaries, reserved for future
  trend detection.

## Response contract (`AIAnalysisResponse`)

- `request_id`, `timestamp`, `model_version` — traceability and versioning.
- `risk_level` — strictly one of `Low`, `Medium`, `High`.
- `risk_score` — float, `0.0`–`100.0`.
- `reason` — human-readable explanation (placeholder until later phases add
  real logic).
- `alert_recipient` — required; `none` / `care_team` / `physician` /
  `emergency_services`.
- `follow_up_action` — always present, but nullable free-text action
  (`null` until later phases implement follow-up generation; if provided it
  cannot be an empty string).

Every response field above is always present, so the backend can rely on one
predictable shape.

## Validation

All validation is enforced by Pydantic v2 models: required fields, strict
primitive types (no silent numeric-string or bool coercion on IDs, counts,
or scores), enum values, numeric ranges, non-empty strings (IDs, symptoms,
medication names, medical-history entries, `reason`, `model_version`,
`follow_up_action`), nested objects, and unexpected fields (extra fields are
rejected). Invalid requests return `422` with a structured `errors` list
(see `app/core/exceptions.py`).

## Running

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

## Integration notes

The AI Engine receives all required data in the request body — it does not
query a database or assume any backend framework. The backend gathers
patient data and calls `POST /api/v1/analyze` with a payload matching
`AIAnalysisRequest`. Until Phase 1+ implements real risk analysis, that
endpoint validates the request and responds `501 Not Implemented`.

## Future AI/model technology

Phase 0 only needs FastAPI, Uvicorn, and Pydantic — no model or data-science
libraries are installed at this stage, and none are implied to be fixed.
The technology used for actual risk-analysis and model implementation in
later phases is not locked in yet. It will be chosen deliberately based on
accuracy/performance, explainability, reliability, suitability for the data
actually available, maintainability, development speed, hackathon
demonstration value, and future extensibility.
````
