"""Builds the Doctor Agent's `ToolRegistry` (Phase 2).

Deliberately a separate registry from the Phase 1 default one
(`app/agents/tools/default_registry.py`), per the Phase 1 README's own
guidance for adding a new agent: a role gets its own registry rather than
the shared default being edited or grown unboundedly. Reuses
`get_patient_basic_info` unchanged from Phase 1.
"""

from app.agents.tools.base import ToolRegistry
from app.agents.tools.doctor_tools import (
    get_medication_adherence,
    get_patient_history,
    get_patient_medications,
    get_patient_risk,
    search_patient_records,
)
from app.agents.tools.patient_tools import get_patient_basic_info


def build_doctor_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(get_patient_basic_info)
    registry.register(get_patient_medications)
    registry.register(get_medication_adherence)
    registry.register(get_patient_risk)
    registry.register(get_patient_history)
    registry.register(search_patient_records)
    return registry
