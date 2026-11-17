import importlib

import pytest

from tests.fake_llm import get_test_llm


@pytest.fixture
def fixture_llm(monkeypatch):
    # Patch every module that imports the factory by name. Real model code is untouched.
    for name in (
        "common.llm", "exercises.exercise_2_tools", "exercises.exercise_4_multiagent",
        "stages.stage_1_direct_llm.main", "stages.stage_2_rag_tools.main",
        "stages.stage_3_single_agent.main", "stages.stage_4_multi_agent.main",
        "law_agent.graph", "customer_agent.graph", "tax_agent.graph", "compliance_agent.graph",
    ):
        module = importlib.import_module(name)
        monkeypatch.setattr(module, "get_llm", get_test_llm)
