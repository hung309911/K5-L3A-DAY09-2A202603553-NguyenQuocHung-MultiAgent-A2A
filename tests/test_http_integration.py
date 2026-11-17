import json
from uuid import uuid4

import httpx
import pytest

from common.a2a_client import delegate
from tests.http_harness import ROOT, ServiceCluster, free_port

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def cluster():
    with ServiceCluster() as services:
        yield services
        reports = ROOT / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "a2a-evidence.json").write_text(
            json.dumps(services.evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )


def test_all_services_register_and_publish_cards(cluster):
    with httpx.Client(trust_env=False) as client:
        response = client.get(cluster.url("registry") + "/agents")
        assert len(response.json()["agents"]) == 4
        for name in ("customer_agent", "law_agent", "tax_agent", "compliance_agent"):
            card = client.get(cluster.url(name) + "/.well-known/agent-card.json").json()
            assert card["url"] == cluster.url(name)
            assert card["skills"]
    cluster.evidence["checks"].append({"check": "registry_and_cards", "passed": True, "service_count": 5})


async def test_full_a2a_chain_preserves_trace_context_and_depth(cluster):
    context_id = str(uuid4())
    trace_id = "day9-trace-" + str(uuid4())
    answer = await delegate(cluster.url("customer_agent"), "tax compliance contract", context_id, trace_id, 0)
    for marker in ("[FIXTURE:LAW]", "[FIXTURE:TAX]", "[FIXTURE:COMPLIANCE]"):
        assert marker in answer
    expected = {"customer_agent": 0, "law_agent": 1, "tax_agent": 2, "compliance_agent": 2}
    trace_lines = {}
    for name, depth in expected.items():
        lines = [line for line in cluster.read_log(name).splitlines() if "executing |" in line and trace_id in line]
        assert len(lines) == 1, f"Missing or duplicated trace in {name}: {lines}"
        assert f"context={context_id}" in lines[0]
        assert f"depth={depth}" in lines[0]
        trace_lines[name] = lines[0]
    cluster.evidence["checks"].append({
        "check": "full_a2a_chain", "passed": True, "trace_id": trace_id,
        "context_id": context_id, "trace_lines": trace_lines, "answer": answer,
    })


async def test_tax_shutdown_partial_result_and_dynamic_rediscovery(cluster):
    old_endpoint = cluster.url("tax_agent")
    cluster.stop("tax_agent")
    answer = await delegate(
        cluster.url("customer_agent"), "tax compliance contract", str(uuid4()), "day9-tax-down", 0,
    )
    assert "Tax analysis unavailable" in answer
    assert "[FIXTURE:COMPLIANCE]" in answer
    # Restart on a different port, proving that the caller actually rediscovers the service.
    new_port = free_port()
    while new_port in cluster.ports.values():
        new_port = free_port()
    cluster.ports["tax_agent"] = new_port
    cluster.start("tax_agent", append=True)
    with httpx.Client(trust_env=False) as client:
        info = client.get(cluster.url("registry") + "/discover/tax_question").json()
    assert info["endpoint"] == cluster.url("tax_agent") != old_endpoint
    recovered = await delegate(
        cluster.url("customer_agent"), "tax compliance contract", str(uuid4()), "day9-tax-recovered", 0,
    )
    assert "[FIXTURE:TAX]" in recovered
    assert "Tax analysis unavailable" not in recovered
    cluster.evidence["checks"].append({
        "check": "tax_shutdown_and_dynamic_rediscovery", "passed": True,
        "old_endpoint": old_endpoint, "new_endpoint": info["endpoint"],
        "partial_answer": answer, "recovered_answer": recovered,
    })
