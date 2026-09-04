"""The Doctor Agent's tool registry contains exactly the six intended
tools - no more (no unnecessary tools), no less."""

from app.agents.tools.doctor_registry import build_doctor_registry


def test_doctor_registry_has_exactly_the_six_intended_tools():
    registry = build_doctor_registry()
    names = {decl["name"] for decl in registry.function_declarations()}

    assert names == {
        "get_patient_basic_info",
        "get_patient_medications",
        "get_medication_adherence",
        "get_patient_risk",
        "get_patient_history",
        "search_patient_records",
    }


def test_every_doctor_tool_requires_patient_id():
    registry = build_doctor_registry()
    for decl in registry.function_declarations():
        assert "patient_id" in decl["parameters_json_schema"]["required"], decl["name"]
