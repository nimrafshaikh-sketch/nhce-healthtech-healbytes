# HealBytes AI Engine

Backend-agnostic FastAPI service that analyzes a patient check-in and
returns a structured risk assessment. Phase 0 established the
request/response contract; Phase 1 added a deterministic current-check-in
risk baseline; Phase 2 added a small, bounded historical-trend adjustment;
Phase 3 added a small, bounded medication-adherence adjustment; Phase 4
added a deterministic follow-up recommendation; Phase 5 (current) adds a
controlled AI explanation layer. **None of this is a clinical diagnostic
system** — see the Phase 1, Phase 2, Phase 3, Phase 4, and Phase 5 sections
below for the full disclaimers.

## Structure

- `app/schemas/` — Pydantic request (`request.py`) and response
  (`response.py`) contracts, plus shared enums (`common.py`). **Fixed
  contract — do not change without a genuine blocker.**
- `app/analysis/` — the risk-analysis pipeline:
  - `risk_engine.py` — Phase 1 current-check-in baseline scorer.
  - `trend_detector.py` — Phase 2 historical-trend heuristic.
  - `medication_adherence.py` — Phase 3 medication-adherence heuristic.
  - `follow_up_recommender.py` — Phase 4 deterministic follow-up recommendation engine.
  - `explanation_service.py` — Phase 5 controlled AI explanation layer.
  - `risk_assessor.py` — orchestrator: baseline + bounded trend + bounded
    medication adjustment.
  - `response_builder.py` — maps the combined result, follow-up recommendation, and AI explanation onto the response
    contract.
- `app/api/routes.py` — `/health` and `/analyze` endpoints. `/analyze`
  validates the request, runs the risk pipeline, and returns `200` with a
  full `AIAnalysisResponse` (or `422` if the request itself is invalid).
- `app/core/` — logging setup and centralized validation-error handling.
- `app/config.py` — environment-driven settings.
- `tests/` — schema, engine, trend, medication, assessor, and API contract
  tests.

## Request contract (`AIAnalysisRequest`)

- `patient_id`, `request_id`, `timestamp` — request metadata for
  traceability.
- `check_in` — `symptoms`, `severity` (`mild`/`moderate`/`severe`),
  `duration` (value + unit).
- `medical_context` — `medical_history`, and `medication_adherence` records
  (each with `medication_name`, `adherence_status`, optional `last_taken`).
  As of Phase 3, `adherence_status` on each record is used by the
  medication heuristic below; `medication_name` and `last_taken` remain
  observed-but-unused (no per-medication identity, dosage, or timing logic
  exists in Phase 3).
- `historical_context` — `previous_checkins` summaries. As of Phase 2, the
  `severity` and `timestamp` of each entry are used by the trend heuristic
  below; `risk_level` remains observed-but-unused (see Phase 2 section).

No new request or response fields were introduced in Phase 3 — medication
adherence is analyzed using exactly the `medication_adherence` data already
present in the Phase 0 contract.

## Response contract (`AIAnalysisResponse`)

- `request_id`, `timestamp`, `model_version` — traceability and versioning.
  `model_version` is currently `rule-engine-v4`, identifying the composed
  Phase 1 baseline + Phase 2 bounded-trend + Phase 3 bounded-medication +
  Phase 4 deterministic follow-up recommendation pipeline (see below).
- `risk_level` — strictly one of `Low`, `Medium`, `High`, produced by the
  baseline score after the Phase 2 trend and Phase 3 medication adjustments
  are applied and clamped.
- `risk_score` — float, `0.0`–`100.0`; the Phase 1 baseline plus the bounded
  Phase 2 trend adjustment plus the bounded Phase 3 medication adjustment,
  clamped to this range.
- `reason` — a factor-based explanation combining the Phase 1 baseline
  factors, the Phase 2 trend heuristic, and the Phase 3 medication heuristic
  (see below); never a generic placeholder.
- `alert_recipient` — required; `none` / `care_team` / `physician` /
  `emergency_services`. This is a placeholder classification derived only
  from the final `risk_level` (see below) — no notification is sent.
- `follow_up_action` — required non-empty string in serialized output;
  populated deterministically in Phase 4 by `follow_up_recommender.py`
  according to the final `risk_level` (see Phase 4 section below).
- `explanation` — optional non-empty string in serialized output; populated
  in Phase 5 by `explanation_service.py` downstream of the final risk
  assessment and care-coordination action (see Phase 5 section below).

Every response field above is always present, so the backend can rely on one
predictable shape.

## Phase 1 — deterministic rule-based risk engine

`app/analysis/risk_engine.py` implements the first real analysis behind the
Phase 0 contract. **It is a hackathon/MVP engineering baseline, not a
clinical diagnostic system.** It does not identify, predict, or imply any
medical condition, and its thresholds are hand-picked for a deterministic
demo, not medically validated. It exists behind a narrow seam
(`assess(request) -> RiskAssessment`) so a future ML model can replace it
without changing the API route or the response schema.

**Request fields used as risk signals:**
- `check_in.severity`
- `check_in.duration`
- `check_in.symptoms` (count only, not the symptom text/identity)
- `medical_context.medical_history` (presence only, as a small flat modifier)

**Request fields not analyzed by the Phase 1 baseline itself (used
elsewhere in the pipeline):**
- `medical_context.medication_adherence` — used starting in Phase 3 (see
  below), not by the Phase 1 baseline itself.
- `historical_context.previous_checkins` — used starting in Phase 2 (see
  below), not by the Phase 1 baseline itself.

**Scoring methodology** (`risk_score`, 0-100, additive and clamped):
- Severity: `mild` = 15, `moderate` = 40, `severe` = 70.
- Duration (converted to hours): ≤24h = +0, ≤72h = +10, ≤168h = +20, >168h = +30.
- Symptom count: 1 symptom = +0, 2–3 symptoms = +10, 4+ symptoms = +20.
- Medical history: any entry present = +5, otherwise +0.
- The sum is clamped to `[0, 100]`.

**Risk-level boundaries** (inclusive):
- `Low`: score 0–34
- `Medium`: score 35–69
- `High`: score 70–100

**Alert-recipient placeholder mapping** (response classification only — no
notification is queued or sent, and `emergency_services` is never produced
through Phase 3; the mapping is applied to the *final* risk level, i.e.
after the Phase 2 trend and Phase 3 medication adjustments below):
- `Low` → `none`
- `Medium` → `care_team`
- `High` → `physician`

**`follow_up_action`**: always `null` through Phase 3. Real follow-up
recommendation generation is a later phase.

**`model_version`**: `rule-engine-v3` (bumped `v1` → `v2` in Phase 2, `v2` →
`v3` in Phase 3 — see below), used consistently by the engine, the
orchestrator, the response builder, and the tests.

**Determinism**: the baseline scorer is pure and stateless — identical
current-check-in input always produces an identical score and reason.

**Limitations**: this is an engineering baseline for follow-up
prioritization, not a medical tool. It should not be presented to clinicians
or patients as diagnostic, and its rule weights should be revisited by a
domain expert (or replaced by a trained model) before any real-world use.

## Phase 2 — bounded historical-trend adjustment

`app/analysis/trend_detector.py` adds a small, secondary signal on top of
the Phase 1 baseline, using the check-in history the backend supplies.
**Like Phase 1, this is a deterministic, rule-based, explainable MVP/
hackathon engineering heuristic. It is not clinically validated, not a
diagnostic system, and not a substitute for medical judgment.** It does not
predict disease, diagnosis, deterioration, hospitalization, or emergency
events — it only produces a bounded nudge to a follow-up-prioritization
score, based on the pattern of previously reported severities.

**Observed data vs. engineering inference.** The `reason` text and this
heuristic explicitly separate the two:
- *Observed* (taken directly from the request, never interpreted): each
  historical check-in's `severity` and `timestamp`, and how many historical
  check-ins were supplied. (`risk_level` on historical entries is also
  observed data, but is intentionally not used by this heuristic — see
  below.)
- *Engineering inference* (derived by this module's rules): the
  `improving` / `worsening` / `stable` / `insufficient_data` classification,
  its `weak`/`strong` confidence, and the resulting score adjustment.
  The `reason` field always frames these as a heuristic pattern observation
  from the supplied data — never as a medical conclusion.

**Evidence requirement.** A trend is never inferred from a single
historical comparison:
- Fewer than 2 historical check-ins → `insufficient_data`, adjustment `0`.
- 2 historical check-ins, consistently increasing/decreasing → a directional
  trend, but only `weak` confidence.
- 3+ historical check-ins, consistently increasing/decreasing → `strong`
  confidence.
- Anything not consistently monotonic (flat, or mixed direction) → `stable`,
  adjustment `0`. A trend is never forced onto noisy data.

**Heuristic mechanics.** Historical check-ins are sorted chronologically by
`timestamp` (tie-broken by `request_id` for full determinism), then each
`severity` is mapped to an engineering ordinal (`mild`=1, `moderate`=2,
`severe`=3 — an ordering for comparison only, not a clinical scale). If the
ordinal sequence is strictly increasing, the trend is `worsening`; if
strictly decreasing, `improving`; otherwise `stable`.

**Bounded score adjustment — current check-in stays primary:**
- `weak` trend: ±4 points. `strong` trend: ±8 points. `stable` /
  `insufficient_data`: 0 points.
- Both magnitudes are fixed constants, deliberately kept smaller than the
  smallest possible Phase 1 baseline score (`mild` severity alone = 15
  points) — historical trend can only ever nudge the score, never dominate
  or override the current check-in.
- The adjustment is added to the Phase 1 baseline score and the combined
  total is clamped back to `[0, 100]` before being reclassified into
  `Low`/`Medium`/`High` using the same thresholds as Phase 1.
- Because the maximum possible adjustment (8) is far smaller than the gap
  between the `Low` and `High` bands (at least 36 points), historical trend
  can shift the result by at most one adjacent risk band — it is
  mathematically impossible for a weak historical pattern to turn an
  obviously low-risk check-in into a high-risk one, or vice versa. This is
  enforced by an explicit test (`tests/test_risk_assessor.py`) that checks
  every possible baseline/adjustment combination.

**Composition.** `app/analysis/risk_assessor.py` is the single place that
combines the Phase 1 baseline with the Phase 2 trend adjustment (and, as of
Phase 3, the medication adjustment below); each can be replaced
independently (e.g. by a future trained model) without touching
`app/api/routes.py` or the response schema.

**Limitations**: like Phase 1, this heuristic's weights and thresholds are
engineering defaults for a hackathon MVP, not medically derived or
clinically validated. It should never be presented as predicting a medical
outcome, and should be reviewed by a domain expert (or replaced by a
trained model) before any real-world use.

## Phase 3 — bounded medication-adherence adjustment

`app/analysis/medication_adherence.py` adds a second small, secondary
signal on top of the Phase 1 baseline (composed alongside the Phase 2
trend adjustment), using only the `medication_adherence` records already
present in the Phase 0 request contract. **Like Phase 1 and Phase 2, this
is a deterministic, rule-based, explainable MVP/hackathon engineering
heuristic. It is not clinically validated, not a diagnosis, not a
medication-safety judgment, not a substitute for a doctor, and not an
emergency detector.** Adherence status alone does not establish medical
risk.

**Input data used.** Only `adherence_status`
(`adherent` / `partially_adherent` / `non_adherent` / `unknown`) from each
`MedicationAdherenceRecord` is read. `medication_name` and `last_taken` are
accepted by the contract but not analyzed — there is no per-medication
identity, dosage, schedule, interaction, refill, or timing logic. No new
request fields (dosage, prescription schedule, diagnosis, pharmacy data,
refill history, start/end dates, physician instructions, adverse effects,
vital signs, etc.) were added; Phase 3 works with exactly the
`medication_name` + `adherence_status` (+ optional `last_taken`) already in
the schema.

**Adherence states and their engineering contribution:**
- `adherent` → **+0**. No adherence concern is indicated by the supplied
  data; risk is never artificially increased for a well-adhering patient.
- `partially_adherent` → **+3**. The data indicates some adherence concern.
- `non_adherent` → **+5**. The data indicates a stronger adherence concern
  — this does **not** mean the patient is "medically high-risk," only that
  this heuristic assigns it the largest single-record engineering weight.
- `unknown` → **+0**. Insufficient information is not treated as
  non-adherence; missing data is never punished.

All four values are engineering heuristics chosen for this hackathon MVP,
not medically validated weights.

**Bounded total — current check-in stays primary:**
- Each supplied record's contribution is summed, then the result is capped
  at `MEDICATION_ADJUSTMENT_MAX = 5`. One non-adherent record already
  reaches the cap; any number of additional concerning records (whether
  `partially_adherent` or `non_adherent`, for one medication or many)
  cannot push the contribution past +5. `unknown` records never add
  anything, regardless of how many are present.
- `MEDICATION_ADJUSTMENT_MAX` (5) is deliberately smaller than the smallest
  possible Phase 1 baseline score (`mild` severity alone = 15) — and even
  combined with the maximum Phase 2 trend adjustment (8), the total
  secondary contribution (13) still stays below that same 15-point floor.
  Medication adherence can only ever nudge the score; it can never
  independently create a `High` result from an otherwise low baseline,
  override a clearly high current-condition assessment, or replace
  symptom/severity/duration or historical-trend analysis.
- The medication adjustment is added to the Phase 1 baseline (already
  combined with the Phase 2 trend adjustment) and the total is clamped to
  `[0, 100]`, then reclassified with the **same, unchanged** `Low`
  (0–34) / `Medium` (35–69) / `High` (70–100) thresholds used since Phase 1.
  No new bands were introduced.

**Observed data vs. engineering inference**, mirrored in the `reason` text
exactly as in Phase 2:
- *Observed*: each record's `adherence_status`, and how many records were
  supplied.
- *Engineering inference*: the per-status point contribution, whether the
  raw total was bounded, and the resulting `score_adjustment`. The `reason`
  field always frames this as a heuristic pattern observation from the
  supplied data — never as a medical conclusion, and never inventing
  explanations such as "the medication failure caused deterioration" or
  "the patient requires emergency treatment."

**Determinism**: pure function, no I/O — identical adherence records always
produce an identical adjustment and reason text.

**Out of scope** (not implemented in Phase 3 or anywhere in this codebase):
predicting whether a medication will work, predicting side effects or drug
interactions, predicting hospitalization or disease progression from
adherence, recommending or changing a medication or dosage, starting or
stopping a medicine, or replacing physician instructions. Phase 3 does not
introduce `emergency_services` routing, and does not send any real alert,
email, SMS, or push notification.

**Limitations**: like Phase 1 and Phase 2, these weights are engineering
defaults for a hackathon MVP, not medically derived or clinically
validated, and should be reviewed by a domain expert (or replaced by a
trained model) before any real-world use.

## Phase 4 — deterministic follow-up recommendation engine

`app/analysis/follow_up_recommender.py` adds a deterministic care-coordination
follow-up recommendation based strictly on the final `risk_level` produced by
the preceding pipeline stages (Phase 1 baseline + Phase 2 trend + Phase 3
medication adherence). **Like all preceding phases, this is a deterministic,
rule-based, explainable MVP/hackathon engineering heuristic. It is not
clinically validated, not a diagnosis, not a treatment plan, not a
prescription engine, not a medication recommendation, and not an emergency
detector.**

**Core architectural rule — no feedback into risk scoring:**
- Phase 4 takes the final `RiskLevel` as read-only input.
- Phase 4 does **NOT** modify, recalculate, or alter `risk_score` or `risk_level`.
- The data flow is strictly unidirectional:
  $$\text{Phase 1} + \text{Phase 2} + \text{Phase 3} \longrightarrow \text{final risk\_score} \longrightarrow \text{final risk\_level} \longrightarrow \text{Phase 4 follow\_up\_action}$$

**Deterministic mapping:**
- `Low` $\longrightarrow$ `"Continue routine monitoring and complete the next scheduled check-in."`
  A routine monitoring/coordination action indicating no immediate escalation is needed.
- `Medium` $\longrightarrow$ `"Care-team review and closer follow-up are recommended."`
  A care-team review action for closer coordination.
- `High` $\longrightarrow$ `"Prompt physician review is recommended based on the current risk assessment."`
  A care-coordination action recommending prompt physician review.

**Safety and care-coordination scope:**
- **No emergency services:** Even for `High` risk, this module never recommends calling emergency services, 911, an ambulance, or going to an emergency room. The system does not possess clinical context to make emergency determinations.
- **No medical treatment recommendations:** This module never prescribes, changes, starts, or stops medications, never suggests dosages, and never provides disease-specific treatment plans.
- **Determinism:** Pure, stateless mapping — identical risk levels always yield identical follow-up recommendations.

**Out of scope** (not implemented in Phase 4 or anywhere in this codebase):
clinical treatment plans, diagnostic conclusions, emergency routing, medication changes/dosages, automated doctor dispatch, patient messaging, or notification delivery.

## Phase 5 — Controlled AI explanation layer

`app/analysis/explanation_service.py` provides a controlled, failure-isolated
explanation of the already-computed deterministic risk assessment and
follow-up action. Its purpose is to enhance readability for doctors and care
teams, improve explainability, and support hackathon demonstration value —
**without altering or feeding back into the deterministic risk scoring.**

**Downstream architecture — deterministic engine remains source of truth:**
```text
Phase 1 Baseline + Phase 2 Trend + Phase 3 Medication Adherence
                         │
                         ▼
                  final risk_score
                         │
                         ▼
                  final risk_level
                         │
                         ▼
            Phase 4 follow_up_action
                         │
                         ▼
        Phase 5 AI Explanation Layer
```
- The explanation service is strictly downstream and observational.
- It **never** calculates or recalculates risk, and **never** modifies `risk_score`, `risk_level`, `alert_recipient`, or `follow_up_action`.
- The deterministic pipeline's `model_version` remains `rule-engine-v4` (the explanation layer is an enhancement on top of the deterministic rule engine, not a new risk model version).

**Deterministic fallback (default operational path):**
A pure, deterministic fallback is always available and requires no LLM SDK, network connection, or API keys:
- `Low` $\longrightarrow$ `"The assessment indicates Low risk (score: {score:.1f}/100) based on the deterministic evaluation of reported symptoms, duration, and context. {follow_up_action}"`
- `Medium` $\longrightarrow$ `"The assessment indicates Medium risk (score: {score:.1f}/100) based on the deterministic evaluation of reported symptoms, duration, and context. {follow_up_action}"`
- `High` $\longrightarrow$ `"The assessment indicates High risk (score: {score:.1f}/100) based on the deterministic evaluation of reported symptoms, duration, and context. {follow_up_action}"`

**Pluggable provider abstraction and failure isolation:**
- Implements `ExplanationProvider` protocol supporting pluggable LLM providers.
- If a provider throws an exception, times out, returns an empty/whitespace string, returns an excessively long response (> 1000 characters), or fails safety validation, the service **immediately and safely falls back** to the deterministic template.
- Provider failures never raise a 500 error or disrupt API availability.

**Strict safety and consistency validation:**
- **Contradiction prevention:** Rejects any provider explanation that contradicts the authoritative `RiskLevel` (e.g., claiming High/Medium when the assessment is Low).
- **Forbidden clinical content:** Rejects candidate text containing medical diagnoses, disease declarations, treatment prescriptions, medication alterations, dosage adjustments, or emergency service instructions.
- **Privacy and data minimization:** Only minimal structured assessment summary fields (`risk_level`, `risk_score`, `reason`, `alert_recipient`, `follow_up_action`) are supplied to the explanation service; no raw patient identifiers or sensitive records are forwarded.

**Limitations & out of scope:**
- Plain engineering heuristic for care-coordination presentation; not a clinically validated model, diagnostic tool, treatment planner, or emergency triage system.
- Explicitly out of scope: conversational chatbots, patient messaging, autonomous doctor communication, RAG, vector databases, or multi-agent orchestration.

## Patient History Summary (`app/history/`, `/api/v1/history/summary`)

A second, independent capability alongside `/analyze` — not part of the
Phase 0-5 numbering above, and not touching any of it. `/analyze` assesses
one current check-in; `/api/v1/history/summary` takes a patient's supplied
history (check-ins, medications, lab tests, appointments, and medication
reminder-dispatch logs) and returns a structured, deterministic clinical
summary. Like `/analyze`, the AI Engine has no database access — every
record the summary is computed from is supplied by the caller in the
request body (see `app/history/schemas.py`).

**Contract stability**: `PatientHistoryRequest` and `PatientHistorySummaryResponse`
(`app/history/schemas.py`) are evolved additively only — new optional
request fields with safe defaults, new always-or-conditionally-present
response fields. Existing fields are never renamed, retyped, or removed
without a genuine blocker, exactly like the `/analyze` contract.

**Request** (`PatientHistoryRequest`): `patient_id`, `request_id`, optional
`as_of` (defaults to current UTC time), and five history lists — `checkins`,
`medications`, `lab_tests`, `appointments`, `medication_reminder_logs` — all
defaulting to `[]`. Field names and enum values mirror the real backend
serializers (`backend/apps/checkins`, `apps/medications`, `apps/labtests`,
`apps/appointments`) exactly; no backend field is invented, and where the
backend has no field (e.g. lab result units/reference ranges), none is
added here either.

**Response** (`PatientHistorySummaryResponse.history`, a `PatientHistory`):
- `checkin_count`, `days_since_last_checkin`, `latest_checkin` — deterministic
  counting and date arithmetic.
- `symptom_trend` — reported-symptom-count trend (`improving`/`worsening`/
  `stable`/`insufficient_data`) across chronologically ordered check-ins;
  requires at least 2 check-ins.
- `vital_trend` — per-vital-key directional comparison (`increasing`/
  `decreasing`/`stable`) between the latest check-in and the most recent
  prior reading of that same key.
- `medications` — currently-active medications (`is_active` and within
  `start_date`/`end_date` as of `as_of`, inclusive both ends — mirrors the
  real `Medication.is_active_on()` model method exactly).
- `latest_lab` — the most recent completed lab result. Selection is
  two-tiered: any lab with a real `result_date` always outranks one with
  only a `created_at` fallback, regardless of raw timestamp value; see
  `LabTestRecord`'s docstring for why `created_at` must be the lab
  *result's* recorded time, never the lab *request's* order time.
- `open_follow_up` — the soonest still-**upcoming** appointment with status
  `scheduled` or `confirmed` (`scheduled_at >= as_of`). A `scheduled`/
  `confirmed` appointment already in the past is excluded, not selected —
  it can never mask a genuine future appointment. `completed`/`cancelled`/
  `no_show` are always excluded. `null` when nothing open is upcoming.
- `medication_adherence` — see below.

**Medication adherence** (`compute_medication_adherence` in
`app/history/summary_service.py`) is the AI Engine's first real
*computation* of a medication-adherence classification from data — Phase 3
of `/analyze` (`medication_adherence.py`) only ever consumed an
already-known `adherence_status`; nothing before this produced one.
**Deterministic, engineering-heuristic, not clinically validated** — same
disclaimer class as every other module in this codebase.

- Input: `medication_reminder_logs`, mirroring the real backend's
  `MedicationReminderLog` model (`scheduled_for`, `sent_at`, `acknowledged_at`)
  — one row per reminder actually dispatched for a medication.
- Every medication supplied is evaluated (not only currently-active ones) —
  a just-ended medication's adherence history is still relevant context.
- Per medication: `reminders_sent` and `reminders_acknowledged` are counted
  from the matching reminder logs (`medication_id`); `adherence_rate =
  acknowledged / sent`. Zero matching reminder logs → `unknown`, `rate =
  null` — missing data is never penalized, exactly like the Phase 3
  `/analyze` heuristic's treatment of `unknown` adherence.
- Rate thresholds (hand-picked engineering defaults, not medically derived):
  `rate >= 0.8` → `adherent`; `0.5 <= rate < 0.8` → `partially_adherent`;
  `rate < 0.5` → `non_adherent`.
- `overall_status` is a worst-observed-status rollup across all evaluated
  medications: any `non_adherent` medication makes the overall status
  `non_adherent` regardless of how many others are fine; else any
  `partially_adherent` makes it `partially_adherent`; else `adherent` if at
  least one medication was evaluable and fine; else `unknown`.
- Reuses the existing, fixed `MedicationAdherenceStatus` vocabulary from
  `app/schemas/common.py` (the same one Phase 3 of `/analyze` already
  defines) rather than introducing new categories.

**Backward compatibility**: `medication_reminder_logs` on the request and
`medication_adherence` on the response were both added after the endpoint's
initial release, purely additively. A caller that never sends
`medication_reminder_logs` still gets a valid `200` with `medication_adherence
.overall_status == "unknown"` for every medication — no existing integration
breaks.

**Out of scope** (not implemented here, for the same reasons as every other
module in this codebase): no RAG, no vector database, no external medical
API, no ML/LLM-derived adherence prediction, no medication-safety judgment,
no diagnosis, no automated notification delivery, no database access.

## Agent foundation (Gemini) + Doctor Agent

A separate, independent capability alongside `/analyze` and
`/history/summary`: `app/agents/` adds a shared Gemini + agent + tool
foundation (`POST /api/v1/agents/patient-summary`) plus, on top of it, a
Doctor Agent (`POST /api/v1/agents/doctor`) that lets an authenticated
doctor ask natural-language questions about one of their patients -
answered by Gemini calling into six existing, read-only capabilities
(patient info, medications, medication adherence, risk, longitudinal
history, patient-scoped RAG search) through the existing backend's own
auth/RBAC. No Receptionist/Patient agent exists yet. None of this touches,
alters, or feeds into the deterministic pipeline described above. See
`app/agents/README.md` for the full architecture, tool list, security
boundaries, and how to add the next agent.

## Validation

All validation is enforced by Pydantic v2 models: required fields, strict
primitive types (no silent numeric-string or bool coercion on IDs, counts,
or scores), enum values, numeric ranges, non-empty strings (IDs, symptoms,
medication names, medical-history entries, `reason`, `model_version`,
`follow_up_action`, `explanation`), nested objects, and unexpected fields
(extra fields are rejected). Invalid requests return `422` with a structured
`errors` list (see `app/core/exceptions.py`).

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
`AIAnalysisRequest`, and receives a `200` with a full `AIAnalysisResponse`
for a valid request (or `422` if the request itself fails validation). An
unexpected internal error during analysis returns a generic `500` without
leaking internal details.

## Future AI/model technology

Phases 0-5 only need FastAPI, Uvicorn, and Pydantic — the risk-analysis
pipeline (baseline + trend heuristic + medication heuristic + follow-up
recommender + controlled explanation layer) is plain deterministic Python,
not a trained model, so no ML, LLM, external medical API, notification
library, or data-science library is installed at this stage, and none are
implied to be fixed. The technology used for a real (e.g. ML-based)
risk-analysis implementation in later phases is not locked in yet. It will
be chosen deliberately based on accuracy/performance, explainability,
reliability, suitability for the data actually available, maintainability,
development speed, hackathon demonstration value, and future extensibility —
and can replace `app/analysis/risk_engine.py`,
`app/analysis/trend_detector.py`, `app/analysis/medication_adherence.py`,
`app/analysis/follow_up_recommender.py`, and/or
`app/analysis/explanation_service.py` independently, without changing the
API or response contract.
