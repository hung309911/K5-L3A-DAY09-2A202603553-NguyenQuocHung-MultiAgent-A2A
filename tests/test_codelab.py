import asyncio
import importlib
from unittest.mock import AsyncMock
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from common.llm import get_llm
from exercises import exercise_2_tools as ex2
from exercises import exercise_4_multiagent as ex4
from stages.stage_2_rag_tools import main as stage2
from stages.stage_3_single_agent import main as stage3
from stages.stage_4_multi_agent import main as stage4


@pytest.mark.parametrize("value", [None, "", "your_key_here"])
def test_missing_key_has_actionable_error(monkeypatch, value):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    if value is None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENROUTER_API_KEY", value)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        get_llm()


def test_temperature_control_does_not_send_request(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-not-a-real-key")
    assert get_llm().temperature == 0.3
    assert get_llm(temperature=0.1).temperature == 0.1


@pytest.mark.parametrize("module", [ex2, stage2])
@pytest.mark.parametrize("case,expected", [
    ("contract", "UCC"), (" TORT ", "2-3"), ("property", "5 năm"), ("unknown", "Không xác định"),
])
def test_statute_teaching_examples(module, case, expected):
    assert expected in module.check_statute_of_limitations.invoke({"case_type": case})


@pytest.mark.parametrize("query", ["Tôi bị sa thải", "HỢP ĐỒNG LAO ĐỘNG"])
def test_vietnamese_phrase_retrieval(query):
    assert "labor_law" in stage2.search_legal_database.invoke({"query": query})
    assert "labor_law" in ex2.search_legal_knowledge.invoke({"query": query})


@pytest.mark.parametrize("query,expected", [
    ("breach", "Hadley"), ("negligence", "Donoghue"), ("contract", "Carlill"), ("xyz", "Không tìm thấy"),
])
def test_case_law_search(query, expected):
    assert expected in stage3.search_case_law.invoke({"keywords": query})


async def test_react_runs_tool_and_finishes(fixture_llm):
    agent = create_react_agent(model=stage3.get_llm(), tools=[stage3.search_case_law])
    result = await agent.ainvoke({"messages": [("user", "breach of contract")]})
    assert any(isinstance(m, ToolMessage) and "Hadley" in m.content for m in result["messages"])
    assert isinstance(result["messages"][-1], AIMessage)
    assert not result["messages"][-1].tool_calls


@pytest.mark.parametrize("question,expected", [
    ("thuế và dữ liệu GDPR compliance", {"tax_analysis", "privacy_analysis", "compliance_analysis"}),
    ("DỮ LIỆU cá nhân", {"privacy_analysis"}),
    ("contract only", set()),
])
async def test_privacy_graph_routes_and_aggregates_once(fixture_llm, question, expected):
    # Stream updates prove the aggregator runs only after the selected branches finish.
    events = []
    async for update in ex4.build_graph().astream({"question": question}, stream_mode="updates"):
        events.extend(update.items())
    names = [name for name, _ in events]
    assert names.count("aggregate_results") == 1
    updates = {key for _, values in events for key in values}
    assert expected <= updates
    assert ({"tax_analysis", "privacy_analysis", "compliance_analysis"} - expected).isdisjoint(updates)
    final = events[-1][1]["final_response"]
    assert "[FIXTURE:LAW]" in final
    for key in expected:
        assert f"[FIXTURE:{key.split('_')[0].upper()}]" in final


async def test_privacy_specialists_really_run_concurrently(monkeypatch):
    # Each branch must start before any can finish; a sequential graph times out.
    all_started = asyncio.Event()
    started = set()

    def branch(name, field):
        async def run(state):
            started.add(name)
            if len(started) == 3:
                all_started.set()
            await asyncio.wait_for(all_started.wait(), timeout=2)
            return {field: name}
        return run

    monkeypatch.setattr(ex4, "law_agent", lambda state: {"law_analysis": "law"})
    monkeypatch.setattr(ex4, "tax_agent", branch("tax", "tax_analysis"))
    monkeypatch.setattr(ex4, "compliance_agent", branch("compliance", "compliance_analysis"))
    monkeypatch.setattr(ex4, "privacy_agent", branch("privacy", "privacy_analysis"))
    monkeypatch.setattr(ex4, "aggregate_results", lambda state: {"final_response": ",".join(sorted(started))})
    result = await ex4.build_graph().ainvoke({"question": "tax compliance privacy"})
    assert result["final_response"] == "compliance,privacy,tax"


async def test_stage4_keeps_all_specialist_results(fixture_llm):
    result = await stage4.create_graph().ainvoke({"question": "tax compliance data breach"})
    assert result["tax_result"] and result["compliance_result"] and result["privacy_result"]
    for heading in ("Tax Analysis", "Compliance Analysis", "Privacy & Data Protection Analysis"):
        assert heading in result["final_answer"]


@pytest.mark.parametrize("module", [
    "stages.stage_1_direct_llm.main", "stages.stage_2_rag_tools.main",
    "stages.stage_3_single_agent.main", "stages.stage_4_multi_agent.main",
    "exercises.exercise_2_tools", "exercises.exercise_4_multiagent",
])
async def test_each_entry_point_finishes_offline(fixture_llm, capsys, module):
    await importlib.import_module(module).main()
    assert "[FIXTURE:" in capsys.readouterr().out


async def test_law_partial_failure_keeps_successful_branch(fixture_llm, monkeypatch):
    from common import a2a_client, registry_client
    from law_agent.graph import create_graph

    async def discover(task):
        return task

    async def delegate(endpoint, **kwargs):
        if endpoint == "tax_question":
            raise ConnectionError("fixture tax offline")
        return "[FIXTURE:COMPLIANCE] still available"

    monkeypatch.setattr(registry_client, "discover", discover)
    monkeypatch.setattr(a2a_client, "delegate", delegate)
    result = await create_graph().ainvoke({
        "question": "tax compliance", "context_id": "context", "trace_id": "trace", "delegation_depth": 1,
    })
    assert "Tax analysis unavailable" in result["tax_result"]
    assert "still available" in result["final_answer"]


async def test_max_depth_skips_specialist_calls(fixture_llm, monkeypatch):
    from common import registry_client
    from law_agent.graph import create_graph

    discover = AsyncMock(side_effect=AssertionError("must not delegate"))
    monkeypatch.setattr(registry_client, "discover", discover)
    result = await create_graph().ainvoke({
        "question": "tax compliance", "context_id": "context", "trace_id": "trace", "delegation_depth": 3,
    })
    assert result["final_answer"]
    discover.assert_not_called()


@pytest.mark.parametrize("raw,expected", [
    ('{"needs_tax": false, "needs_compliance": true}', (False, True)),
    ('```json\n{"needs_tax": false, "needs_compliance": false}\n```', (False, False)),
    ('{"needs_tax": "false", "needs_compliance": "false"}', (True, True)),
    ('[]', (True, True)), ('not json', (True, True)),
])
async def test_routing_requires_actual_json_booleans(monkeypatch, raw, expected):
    from law_agent import graph
    model = SimpleNamespace(ainvoke=AsyncMock(return_value=AIMessage(content=raw)))
    monkeypatch.setattr(graph, "get_llm", lambda: model)
    result = await graph.check_routing({"question": "fixture", "delegation_depth": 1})
    assert (result["needs_tax"], result["needs_compliance"]) == expected


async def test_customer_depth_guard_prevents_network(fixture_llm, monkeypatch):
    from common import registry_client
    from customer_agent.graph import build_graph
    discover = AsyncMock(side_effect=AssertionError("must not delegate"))
    monkeypatch.setattr(registry_client, "discover", discover)
    result = await build_graph("trace", "context", 3).ainvoke({"messages": [("user", "tax")]})
    assert "Maximum delegation depth" in result["messages"][-1].content
    discover.assert_not_called()


@pytest.mark.parametrize("question,expected", [
    ("thuế", (True, False, False)),
    ("SEC compliance", (False, True, False)),
    ("DỮ LIỆU cá nhân", (False, False, True)),
    ("tax compliance GDPR", (True, True, True)),
    ("rò rỉ thông tin khách hàng", (False, False, False)),
])
async def test_stage4_routing_obeys_codelab_keywords(monkeypatch, question, expected):
    # Exercise 4.2 requires keyword routing; an LLM must not override that policy.
    def unexpected_model_call():
        raise AssertionError("Stage 4 keyword router must not call an LLM")

    monkeypatch.setattr(stage4, "get_llm", unexpected_model_call)
    result = await stage4.check_routing({"question": question})
    assert (result["needs_tax"], result["needs_compliance"], result["needs_privacy"]) == expected
