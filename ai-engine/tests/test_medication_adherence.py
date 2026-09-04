"""Tests for the Phase 3 medication-adherence heuristic.

`assess_medication_adherence` is pure and reads only a list of
`MedicationAdherenceRecord` objects — no request, no current check-in, no
FastAPI, no I/O — so it is tested fully in isolation here.
"""

import inspect

from app.analysis import medication_adherence
from app.analysis.medication_adherence import (
    ADHERENCE_CONTRIBUTION,
    MEDICATION_ADJUSTMENT_MAX,
    MedicationAdherenceRecord,
    MedicationAdherenceStatus,
    assess_medication_adherence,
)

# Forbidden affirmative clinical/medication-recommendation claims: none of
# these should ever appear in reason text produced by this module.
_FORBIDDEN_PHRASES = [
    "diagnosed with",
    "will develop",
    "will be hospitalized",
    "medically accurate",
    "clinically validated risk model",
    "predicts that",
    "increase the dose",
    "decrease the dose",
    "stop taking",
    "start taking",
    "switch medication",
    "this medication is unsafe",
    "requires emergency treatment",
    "caused deterioration",
    "likely to experience a complication",
]


def _record(status: str, name: str = "TestMed") -> MedicationAdherenceRecord:
    return MedicationAdherenceRecord(medication_name=name, adherence_status=status)


# --- Basic states ----------------------------------------------------------


def test_adherent_contributes_zero():
    result = assess_medication_adherence([_record("adherent")])
    assert result.score_adjustment == 0


def test_partially_adherent_contributes_three():
    result = assess_medication_adherence([_record("partially_adherent")])
    assert result.score_adjustment == 3


def test_non_adherent_contributes_five():
    result = assess_medication_adherence([_record("non_adherent")])
    assert result.score_adjustment == 5


def test_unknown_contributes_zero():
    result = assess_medication_adherence([_record("unknown")])
    assert result.score_adjustment == 0


def test_unknown_is_not_treated_as_non_adherent():
    unknown_result = assess_medication_adherence([_record("unknown")])
    non_adherent_result = assess_medication_adherence([_record("non_adherent")])
    assert unknown_result.score_adjustment == 0
    assert unknown_result.score_adjustment != non_adherent_result.score_adjustment


# --- No records supplied ----------------------------------------------------


def test_no_records_contributes_zero_and_is_not_a_false_penalty():
    result = assess_medication_adherence([])
    assert result.score_adjustment == 0
    assert result.observed_record_count == 0
    assert "insufficient" not in result.reason_fragment.lower()


# --- Bounding: cannot exceed +5 regardless of record count/mix ------------


def test_single_non_adherent_reaches_the_cap():
    result = assess_medication_adherence([_record("non_adherent")])
    assert result.score_adjustment == MEDICATION_ADJUSTMENT_MAX


def test_many_non_adherent_records_still_capped_at_five():
    records = [_record("non_adherent", f"med-{i}") for i in range(10)]
    result = assess_medication_adherence(records)
    assert result.score_adjustment == MEDICATION_ADJUSTMENT_MAX


def test_multiple_partial_adherence_records_cannot_exceed_five():
    records = [_record("partially_adherent", f"med-{i}") for i in range(5)]
    result = assess_medication_adherence(records)
    assert result.score_adjustment <= MEDICATION_ADJUSTMENT_MAX
    assert result.score_adjustment == MEDICATION_ADJUSTMENT_MAX  # 5*3=15, clamped


def test_mixed_records_are_bounded():
    records = [
        _record("non_adherent", "a"),
        _record("non_adherent", "b"),
        _record("partially_adherent", "c"),
    ]
    result = assess_medication_adherence(records)
    assert result.score_adjustment == MEDICATION_ADJUSTMENT_MAX  # raw 13, capped


def test_unknown_records_never_contribute_even_when_mixed_with_concerning_ones():
    # Unknown entries add nothing on top of whatever concern is already there.
    with_unknown = assess_medication_adherence(
        [_record("non_adherent", "a"), _record("unknown", "b")]
    )
    without_unknown = assess_medication_adherence([_record("non_adherent", "a")])
    assert with_unknown.score_adjustment == without_unknown.score_adjustment


def test_adjustment_never_exceeds_max_for_any_combination():
    statuses = list(MedicationAdherenceStatus)
    for a in statuses:
        for b in statuses:
            for c in statuses:
                records = [_record(a.value, "a"), _record(b.value, "b"), _record(c.value, "c")]
                result = assess_medication_adherence(records)
                assert 0 <= result.score_adjustment <= MEDICATION_ADJUSTMENT_MAX


def test_contribution_map_never_produces_a_negative_value():
    assert all(value >= 0 for value in ADHERENCE_CONTRIBUTION.values())


# --- Determinism -------------------------------------------------------------


def test_same_input_produces_same_output():
    records = [_record("non_adherent", "a"), _record("partially_adherent", "b")]
    first = assess_medication_adherence(list(records))
    second = assess_medication_adherence(list(records))
    assert first == second


def test_repeated_calls_are_stable():
    records = [_record("partially_adherent")]
    results = [assess_medication_adherence(list(records)) for _ in range(5)]
    assert len({r.score_adjustment for r in results}) == 1
    assert len({r.reason_fragment for r in results}) == 1


# --- Independence from unrelated data ---------------------------------------


def test_medication_name_does_not_affect_the_adjustment():
    a = assess_medication_adherence([_record("non_adherent", "Aspirin")])
    b = assess_medication_adherence([_record("non_adherent", "SomethingElseEntirely")])
    assert a.score_adjustment == b.score_adjustment


def test_does_not_mutate_input_list():
    records = [_record("non_adherent", "a")]
    original_len = len(records)
    assess_medication_adherence(records)
    assert len(records) == original_len
    assert records[0].adherence_status == MedicationAdherenceStatus.NON_ADHERENT


# --- Reason text: observed vs. inference, and no clinical/medical claims ----


def test_reason_reflects_observed_status_counts():
    result = assess_medication_adherence(
        [_record("non_adherent", "a"), _record("adherent", "b")]
    )
    lowered = result.reason_fragment.lower()
    assert "observed" in lowered
    assert "non_adherent" in lowered
    assert "adherent" in lowered


def test_reason_explains_bounding_when_raw_total_exceeds_max():
    records = [_record("non_adherent", "a"), _record("non_adherent", "b")]
    result = assess_medication_adherence(records)
    lowered = result.reason_fragment.lower()
    assert "bounded" in lowered or "maximum" in lowered


def test_reason_for_no_records_says_none_supplied():
    result = assess_medication_adherence([])
    assert "no medication-adherence records were supplied" in result.reason_fragment.lower()


def test_reason_always_carries_the_non_clinical_disclaimer():
    for records in (
        [],
        [_record("adherent")],
        [_record("unknown")],
        [_record("partially_adherent")],
        [_record("non_adherent")],
    ):
        result = assess_medication_adherence(records)
        lowered = result.reason_fragment.lower()
        assert "not a clinically validated" in lowered
        assert "does not establish medical risk" in lowered


def test_reason_never_contains_forbidden_phrases():
    for records in (
        [],
        [_record("adherent")],
        [_record("partially_adherent")],
        [_record("non_adherent")],
        [_record("unknown")],
        [_record("non_adherent", "a"), _record("non_adherent", "b")],
    ):
        result = assess_medication_adherence(records)
        lowered = result.reason_fragment.lower()
        for phrase in _FORBIDDEN_PHRASES:
            assert phrase not in lowered


# --- No network / external I/O (static safety check) ------------------------


def test_module_source_contains_no_network_or_io_imports():
    source = inspect.getsource(medication_adherence)
    forbidden_tokens = [
        "requests",
        "httpx",
        "urllib",
        "socket",
        "http.client",
        "boto3",
        "openai",
        "anthropic",
        "psycopg2",
        "sqlalchemy",
        "smtplib",
    ]
    lowered = source.lower()
    for token in forbidden_tokens:
        assert token not in lowered
