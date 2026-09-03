"""Phase 3 deterministic medication-adherence analysis.

This module is a transparent, rule-based engineering heuristic for
prioritization purposes only. It is explicitly NOT a clinical risk score, a
diagnosis, a medical recommendation, a medication-safety judgment, or a
substitute for a doctor. It never performs a network call, never calls an
LLM or an external (medical or otherwise) API, never touches a database,
and never sends a notification — it is a pure function over the
medication-adherence data already present in the request contract
(`app/schemas/request.py`).

It distinguishes between two kinds of information:

Observed data (taken directly from the request, never interpreted):
    - each `MedicationAdherenceRecord.adherence_status`
      (`adherent` / `partially_adherent` / `non_adherent` / `unknown`)
    - how many medication-adherence records were supplied

Engineering inference (derived by this module's rules, not measured):
    - the per-status point contribution
    - the combined, bounded `score_adjustment`

Design rules enforced here:
    - `adherent` and `unknown` both contribute 0 points. Missing or unknown
      adherence information is explicitly NOT treated as non-adherence and
      is never penalized.
    - `partially_adherent` contributes a small fixed engineering weight of
      +3 points; `non_adherent` contributes +5 points. Neither value is
      medically validated, and neither implies a specific medical outcome,
      complication, or diagnosis — they only flag that the supplied data
      shows some or more adherence concern.
    - Regardless of how many medication records are supplied, the total
      medication contribution can never exceed `MEDICATION_ADJUSTMENT_MAX`
      (5) — one non-adherent record already reaches the cap, and no number
      of additional concerning records can push it higher. This keeps
      medication data from overpowering the current check-in (Phase 1) or
      the historical trend (Phase 2): `MEDICATION_ADJUSTMENT_MAX` is well
      below the smallest possible Phase 1 baseline score (mild severity
      alone = 15; see `risk_engine.SEVERITY_SCORES`).
    - This module never reduces the score: adherence data can only add a
      small contextual concern, never subtract one.
    - Only `adherence_status` is read from each record. `medication_name`
      and `last_taken` are accepted by the Phase 0 contract but are not
      analyzed here — there is no per-medication identity, dosage,
      schedule, interaction, or timing logic in Phase 3.

Out of scope (explicitly not implemented here, or anywhere in Phase 3):
predicting whether a medication will work, predicting side effects or drug
interactions, predicting hospitalization or disease progression from
adherence, or recommending/changing/starting/stopping a medication or
dosage. This module only answers: does the supplied adherence data show
evidence of a concern, and if so, how much should that nudge the score?

ORPHANED as of Phase 6: the agreed backend wire contract
(`backend/apps/checkins/ai_client.py`, `feature/backend` branch) does not
send medication-adherence data, so nothing in the live `/analyze/` pipeline
currently calls `assess_medication_adherence`. This module is kept, working
and tested, in case a future contract revision reintroduces a
`medical_context`-style field — see `README.md`'s Phase 6 section.
`MedicationAdherenceStatus`/`MedicationAdherenceRecord` are now defined
locally below (decoupled from `app/schemas/request.py`, which no longer has
them) purely so this module keeps working standalone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Dict, List, Optional

# --- Local, decoupled types (see module docstring) -----------------------


class MedicationAdherenceStatus(str, Enum):
    """Adherence classification for a single medication. Not part of the
    live Phase 6 request contract; kept here only for this orphaned module."""

    ADHERENT = "adherent"
    PARTIALLY_ADHERENT = "partially_adherent"
    NON_ADHERENT = "non_adherent"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MedicationAdherenceRecord:
    """Adherence status for a single prescribed medication. Not part of the
    live Phase 6 request contract; kept here only for this orphaned module."""

    medication_name: str
    adherence_status: MedicationAdherenceStatus = MedicationAdherenceStatus.UNKNOWN
    last_taken: Optional[date] = None

MEDICATION_ADJUSTMENT_MAX = 5
"""Hard upper bound on the total medication-adherence score contribution,
regardless of how many records are supplied or how concerning they are."""

ADHERENCE_CONTRIBUTION: Dict[MedicationAdherenceStatus, int] = {
    MedicationAdherenceStatus.ADHERENT: 0,
    MedicationAdherenceStatus.PARTIALLY_ADHERENT: 3,
    MedicationAdherenceStatus.NON_ADHERENT: 5,
    MedicationAdherenceStatus.UNKNOWN: 0,
}
"""Per-record engineering heuristic contribution. Not medically validated.
`unknown` is deliberately equal to `adherent` (0): missing information is
never punished."""

MEDICATION_DISCLAIMER = (
    "Medication-adherence status is user/system-provided contextual data. "
    "This adjustment is a deterministic engineering heuristic, not a "
    "clinically validated medication-safety judgment, diagnosis, or "
    "treatment recommendation, and adherence status alone does not "
    "establish medical risk."
)


@dataclass(frozen=True)
class MedicationAssessment:
    """Pure output of the medication-adherence heuristic."""

    score_adjustment: int
    observed_record_count: int
    reason_fragment: str


def _status_counts(records: List[MedicationAdherenceRecord]) -> Dict[MedicationAdherenceStatus, int]:
    counts = {status: 0 for status in MedicationAdherenceStatus}
    for record in records:
        counts[record.adherence_status] += 1
    return counts


def _describe_counts(counts: Dict[MedicationAdherenceStatus, int]) -> str:
    described = [f"{count} {status.value}" for status, count in counts.items() if count > 0]
    return ", ".join(described)


def _build_reason(
    record_count: int,
    counts: Dict[MedicationAdherenceStatus, int],
    raw_total: int,
    bounded_adjustment: int,
) -> str:
    if record_count == 0:
        body = (
            "No medication-adherence records were supplied in this request. "
            "Engineering inference: adherence cannot be assessed from absent "
            "data; no score adjustment applied."
        )
        return f"{body} {MEDICATION_DISCLAIMER}"

    observed = (
        f"Observed {record_count} medication-adherence record(s) "
        f"({_describe_counts(counts)})."
    )

    if bounded_adjustment == 0:
        inference = (
            " Engineering inference: no adherence concern indicated by the "
            "supplied data; no score adjustment applied."
        )
    elif raw_total > bounded_adjustment:
        inference = (
            f" Engineering inference: the combined raw adherence-concern "
            f"contribution ({raw_total} point(s)) exceeds this heuristic's "
            f"maximum, so it is bounded to +{bounded_adjustment} point(s)."
        )
    else:
        inference = (
            f" Engineering inference: adherence-concern contribution of "
            f"+{bounded_adjustment} point(s) applied."
        )

    return f"{observed}{inference} {MEDICATION_DISCLAIMER}"


def assess_medication_adherence(records: List[MedicationAdherenceRecord]) -> MedicationAssessment:
    """Deterministically compute a bounded medication-adherence score
    contribution from the supplied records.

    Reads only `adherence_status` from each `MedicationAdherenceRecord` in
    `records` (typically `request.medical_context.medication_adherence`).
    Never mutates the input, never performs I/O.
    """

    record_count = len(records)
    counts = _status_counts(records)
    raw_total = sum(ADHERENCE_CONTRIBUTION[record.adherence_status] for record in records)
    bounded_adjustment = max(0, min(MEDICATION_ADJUSTMENT_MAX, raw_total))

    reason_fragment = _build_reason(record_count, counts, raw_total, bounded_adjustment)

    return MedicationAssessment(
        score_adjustment=bounded_adjustment,
        observed_record_count=record_count,
        reason_fragment=reason_fragment,
    )
