"""ORPHANED as of Phase 6.

Before Phase 6, this module composed the Phase 1 current-check-in baseline
with the Phase 2 (`trend_detector.py`) and Phase 3 (`medication_adherence.py`)
bounded adjustments, reading `AIAnalysisRequest.check_in`,
`AIAnalysisRequest.medical_context`, and `AIAnalysisRequest.historical_context`.

Phase 6 replaced `app/schemas/request.py` with the agreed backend wire
contract (`backend/apps/checkins/ai_client.py`, `feature/backend` branch),
which sends `checkin_id`/`patient_id`/`symptoms`/`pain_level`/`mood`/
`vitals`/`notes` — none of `check_in`, `medical_context`, or
`historical_context` exist on the current request contract, so there is no
longer a single request this module could validly compose against.

`app/analysis/response_builder.py` now calls `app/analysis/risk_engine.py`
directly. `trend_detector.py` and `medication_adherence.py` remain in the
codebase as working, independently tested heuristics (each now defines its
own decoupled input type) in case a future contract revision reintroduces
historical or medication data — see `README.md`'s Phase 6 section for the
full rationale. This file is intentionally left without composition logic
to avoid presenting a function that looks callable against the live
contract but is not.
"""
