# HealBytes AI Engine

Backend-agnostic FastAPI service that analyzes a patient check-in and
returns a structured risk assessment. **Phase 6 (current)** replaced the
service's request/response contract to match, field for field, what
`backend/apps/checkins/ai_client.py` (`feature/backend` branch) actually
sends and expects — see "Phase 6 — exact wire-contract alignment" below for
why, and for what changed. **None of this is a clinical diagnostic
system.**

## Structure

- `app/schemas/` — Pydantic request (`request.py`) and response
  (`response.py`) contracts, plus shared enums (`common.py`). **Fixed
  contract — do not change without a genuine blocker, and never without
  re-checking `ai_client.py` on `feature/backend`.**
- `app/analysis/` — the risk-analysis pipeline:
  - `risk_engine.py` — deterministic baseline scorer (pain level + symptom
    count). The live pipeline's only scoring module.
  - `follow_up_recommender.py` — deterministic mapping from final risk
    level to `recommendedAction` text.
  - `response_builder.py` — composes `risk_engine` + `follow_up_recommender`
    into the response contract. This is the seam a future ML model could
    replace without touching `app/api/routes.py` or the schema.
  - `trend_detector.py`, `medication_adherence.py`, `explanation_service.py`,
    `risk_assessor.py` — **orphaned** from the live pipeline as of Phase 6
    (see below); kept, working, and independently tested, in case a future
    contract revision reintroduces the data they need.
- `app/api/routes.py` — `POST /analyze/` and `GET /health`.
- `app/core/` — logging setup and centralized validation-error handling.
- `app/config.py` — environment-driven settings.
- `tests/` — schema, engine, and API contract tests, plus isolated unit
  tests for the orphaned modules.

## Request contract (`AIAnalysisRequest`)

Matches `ai_client.py`'s payload exactly:

```json
{
  "checkin_id": 1,
  "patient_id": 1,
  "symptoms": ["headache", "fatigue"],
  "pain_level": 4,
  "mood": "anxious",
  "vitals": {"heart_rate": 78},
  "notes": "Patient reports gradual onset since yesterday."
}
```

- `checkin_id`, `patient_id` — required ints.
- `symptoms` — list of non-empty strings; may be `[]`.
- `pain_level` — optional int; when present, must be `0`-`10`. **This range
  is a documented assumption, not confirmed by `ai_client.py`** (it only
  says `int|null`) — flag with the backend/product owner before relying on
  it (see "Team integration dependency" below).
- `mood` — optional string. Accepted, **not yet scored**: there is no
  agreed vocabulary or risk mapping for it.
- `vitals` — optional free-form object. Accepted, **not yet scored**: the
  contract defines no sub-schema (units, keys, normal ranges).
- `notes` — optional free text. Accepted, **not analyzed** (no NLP/LLM in
  this phase).
- **Insufficient-data safeguard**: at least one of `symptoms` (non-empty)
  or `pain_level` (non-null) is required, or the request is rejected with
  `422` rather than the engine fabricating a score from nothing.

## Response contract (`AIAnalysisResponse`)

Matches `ai_client.py`'s `_parse_response` exactly — five fields, nothing
else (`extra="forbid"`):

```json
{
  "riskLevel": "medium",
  "riskScore": 0.6,
  "reason": "Reported pain level 8/10 contributed 50 point(s). ...",
  "recommendedAction": "Care-team review and closer follow-up are recommended.",
  "notificationRecipient": "caretaker"
}
```

- `riskLevel` — `"low" | "medium" | "high"` (matches
  `ai_client.VALID_RISK_LEVELS` exactly).
- `riskScore` — float, `0.0`-`1.0` (the internal 0-100 rule-engine score
  divided by 100).
- `reason` — factor-based explanation (pain level, symptom count, and a
  note about which received-but-unscored fields were present).
- `recommendedAction` — deterministic `follow_up_recommender` text. There
  is no LLM in this pipeline.
- `notificationRecipient` — `"none" | "caretaker" | "doctor" | "both"`,
  **informational only**: per `ai_client.py`'s own docstring, the backend's
  `apps.alerts.rules` — not this field — decides who is actually alerted.

## Deterministic rule engine (`app/analysis/risk_engine.py`)

**Hackathon/MVP engineering baseline, not a clinical diagnostic system.**
Thresholds are hand-picked, not medically validated.

**Scoring** (0-100, additive, clamped):
- Pain level (0-2 = +0, 3-5 = +25, 6-8 = +50, 9-10 = +75; missing = +0).
- Symptom count (0-1 = +0, 2-3 = +10, 4+ = +25).

**Risk-level boundaries** (inclusive, unchanged since earlier phases):
`low` 0-34, `medium` 35-69, `high` 70-100.

**`notificationRecipient` placeholder mapping** (final risk level only —
no notification is queued or sent): `low` → `none`, `medium` → `caretaker`,
`high` → `doctor`. `both` is never produced by this deterministic mapping.

**Determinism**: pure, stateless — identical input always produces an
identical score and reason.

## Phase 6 — exact wire-contract alignment

Phases 0-5 (see git history) built a richer contract
(`check_in`/`medical_context`/`historical_context`, capitalized
`Low`/`Medium`/`High`, a 0-100 `risk_score`, `alert_recipient`,
`follow_up_action`, an `explanation` layer) against an assumed shape. When
this phase inspected the actual integration point —
`backend/apps/checkins/ai_client.py` on the `feature/backend` branch (not
present in this working tree; read via `git show
origin/feature/backend:backend/apps/checkins/ai_client.py`) — the real,
already-agreed contract turned out to be substantially different: a
different route (`POST {AI_ENGINE_URL}/analyze/`, no version prefix),
different field names and casing, a `0.0`-`1.0` score instead of `0-100`,
and entirely different input fields (`pain_level`/`mood`/`vitals`/`notes`
instead of `severity`/`duration`/`medical_context`/`historical_context`).

Per this project's own rule ("if the repository and plan differ, do not
silently change the backend contract — report the difference first and
implement the smallest compatible solution"), this was reported to the
user before any code changed, and the user chose to adapt the AI Engine to
`ai_client.py` rather than the reverse.

**Consequence**: `trend_detector.py` (historical-trend heuristic) and
`medication_adherence.py` (medication-adherence heuristic) have no data to
read from the new request contract, since `historical_context` and
`medical_context` no longer exist on it. Rather than deleting working,
tested code, both modules were decoupled from `app/schemas/request.py`
(they now define their own local `PreviousCheckInSummary` /
`MedicationAdherenceRecord` types) and left orphaned — importable, tested
in isolation, not called by `response_builder.py`. `risk_assessor.py`
(the module that used to compose baseline + trend + medication against the
old contract) is now a documentation-only stub, since there is no longer a
single request shape for it to compose against.
`explanation_service.py` (Phase 5's LLM-explanation layer, never actually
wired to a real LLM provider) is similarly decoupled and orphaned — the
wire contract has no `explanation` field — but is kept in case a future
revision wants `reason` or `recommendedAction` to be LLM-narrated. If that
happens, the same architectural rule still applies: **an LLM must never
compute `riskScore`.**

If a future contract revision reintroduces historical or medical-context
data, these modules are ready to be reattached in `response_builder.py`
without rewriting their internals.

## Team integration dependency

`backend/apps/checkins/ai_client.py` and the rest of the Django app source
are **not present in this working tree** — only stale `.pyc` bytecode
cache remains under `backend/apps/*/__pycache__/`, no `.py` source, no
`manage.py`. The actual contract used throughout this README was read
read-only from the `origin/feature/backend` remote branch
(`git show origin/feature/backend:backend/apps/checkins/ai_client.py`),
not from local files. Whoever owns the backend module should confirm the
local `backend/` working tree is restored/synced. Separately, the assumed
`pain_level` range (`0`-`10`) is not documented in `ai_client.py` and
should be confirmed with the backend/product owner.

## Validation

All validation is enforced by Pydantic v2 models: required fields, strict
primitive types (no silent numeric-string or bool coercion on IDs or
scores), enum values, numeric ranges, non-empty strings, and unexpected
fields (extra fields are rejected on both request and response). Invalid
requests return `422` with a structured `errors` list (see
`app/core/exceptions.py`, which uses `jsonable_encoder` so a `ValueError`
raised by the "insufficient data" check — or any other `model_validator` —
serializes safely instead of crashing the error response itself).

## Running

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
pytest
```

## Integration notes

The AI Engine receives all required data in the request body — it does not
query a database or assume any backend framework. The backend calls
`POST {AI_ENGINE_URL}/analyze/` (trailing slash, no version prefix) with a
payload matching `AIAnalysisRequest`, and receives a `200` with a full
`AIAnalysisResponse` for a valid request, or `422` if the request itself
fails validation (including the insufficient-data case). An unexpected
internal error during analysis returns a generic `500` without leaking
internal details. `ai_client.py` already treats a failed call, a timeout,
an unconfigured `AI_ENGINE_URL`, or a malformed/unrecognized response as a
safe `"unavailable"` result — a `422` or `500` from this service degrades
the same way, by design.

## Future AI/model technology

This phase only needs FastAPI, Uvicorn, and Pydantic — the risk-analysis
pipeline is plain deterministic Python, not a trained model, so no ML,
LLM, external medical API, notification library, or data-science library
is installed, and none are implied to be fixed. A future (e.g. ML-based)
risk-analysis implementation can replace `app/analysis/risk_engine.py`
independently, without changing the API or response contract.
