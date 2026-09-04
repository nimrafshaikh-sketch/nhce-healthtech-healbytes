"""Builds the default `ToolRegistry` for the AI Engine's agent(s).

A new agent in Phase 2/3 registers its own additional tools the same way -
see `app/agents/README.md` - rather than editing this function's callers
directly; this factory only defines *which* tools exist by default today.
"""

from app.agents.tools.base import ToolRegistry
from app.agents.tools.patient_tools import get_patient_basic_info


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(get_patient_basic_info)
    return registry
