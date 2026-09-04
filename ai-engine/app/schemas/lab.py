"""AI Engine lab-result analysis contract.

Defines the request/response shape for analyzing a single lab test result
submitted by a lab technician. Mirrors the check-in analysis contract's
shape/spirit (app/schemas/request.py, response.py) but for a structured lab
value instead of a symptom check-in. Keyed by the same fixed test_name
choices used in the backend's apps.labtests.models.LabTestRequest.TestName,
per that model's own design intent ("a reliable key to match against" - see
backend/apps/labtests/models.py).
"""

from datetime import datetime
from typing import Optional

from app.schemas.common import NonEmptyStr, RiskLevel, StrictModel


class LabAnalysisRequest(StrictModel):
    """Request payload sent by the backend after a lab technician submits a
    LabTestResult."""

    patient_id: NonEmptyStr
    request_id: NonEmptyStr
    timestamp: datetime

    test_name: NonEmptyStr
    result_text: NonEmptyStr


class LabAnalysisResponse(StrictModel):
    """Structured, validated response returned by the AI Engine for a single
    lab result. `numeric_value`/`unit`/`reference_range` are null when no
    number could be parsed from the free-text result (see
    app/analysis/lab_reference.py); `status` and `explanation` are always
    present."""

    request_id: NonEmptyStr
    timestamp: datetime

    test_name: NonEmptyStr
    numeric_value: Optional[float] = None
    unit: Optional[NonEmptyStr] = None
    reference_range: Optional[NonEmptyStr] = None
    status: NonEmptyStr
    risk_level: RiskLevel
    explanation: NonEmptyStr

    model_version: NonEmptyStr
