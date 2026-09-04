"""RETIRED as of Phase 6.

This file used to test `app.analysis.risk_assessor.assess_with_trend`, the
orchestrator that composed the Phase 1 baseline with the Phase 2 trend and
Phase 3 medication-adherence adjustments against the pre-Phase-6 request
contract (`check_in` / `medical_context` / `historical_context`).

That contract no longer exists — `app/schemas/request.py` was replaced in
Phase 6 to match the agreed backend wire contract
(`backend/apps/checkins/ai_client.py`, `feature/backend` branch), which has
none of those fields. `app/analysis/risk_assessor.py` is now a documentation
-only orphaned module (see its docstring), so there is nothing left here to
exercise.

The underlying heuristics this file used to test through the composed
pipeline are still tested directly and in isolation:
    - `app/analysis/risk_engine.py` -> `tests/test_risk_engine.py`
    - `app/analysis/trend_detector.py` -> `tests/test_trend_detector.py`
      (now decoupled from the live request schema; still fully tested)
    - `app/analysis/medication_adherence.py` -> `tests/test_medication_adherence.py`
      (same)

This file is intentionally left with no test collection content (this
module could not be deleted directly from this working tree — see the
Phase 6 section of README.md's file-safety notes).
"""
