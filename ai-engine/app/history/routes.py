"""API routes for the Phase 2 patient-history summary capability.

Mounted separately from `app/api/routes.py` (Phase 1's `/health` and
`/analyze`) so the two capabilities can be developed, tested, and deployed
independently. Both routers are included under the same `settings.api_prefix`
in `app/main.py`.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.history.schemas import PatientHistoryRequest, PatientHistorySummaryResponse
from app.history.summary_service import build_history_summary

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/history/summary",
    response_model=PatientHistorySummaryResponse,
    tags=["patient-history"],
)
def summarize_patient_history(payload: PatientHistoryRequest) -> PatientHistorySummaryResponse:
    """Validate a patient-history request and return a deterministic,
    structured clinical summary computed only from the supplied records.

    The AI Engine has no database access - all check-ins, medications, lab
    tests, and appointments must be supplied in the request body by the
    caller (see `app/history/schemas.py`).
    """

    logger.info(
        "Summarizing history request %s for patient %s",
        payload.request_id,
        payload.patient_id,
    )
    try:
        return build_history_summary(payload)
    except Exception:
        logger.exception("Unexpected error summarizing history request %s", payload.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while summarizing patient history.",
        )
