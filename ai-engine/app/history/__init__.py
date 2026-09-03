"""Phase 2: patient history / clinical summary module.

A self-contained capability, separate from the Phase 1 `/analyze` contract
in `app/schemas/` and the Phase 1 analysis pipeline in `app/analysis/`.
Nothing in this package is imported by, or modifies, Phase 1.

The AI Engine has no database access. All history data (check-ins,
medications, lab tests, appointments) must be supplied by the caller in the
request body, mirroring the fields the real backend serializers actually
expose (see `app/history/schemas.py`). This module only performs
deterministic, explainable calculations over that supplied data - no ML,
no LLM, no external retrieval.
"""
