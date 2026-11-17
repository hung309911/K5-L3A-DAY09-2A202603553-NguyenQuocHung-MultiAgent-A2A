from types import SimpleNamespace as NS

import pytest
from a2a.types import Message, Part, Role, TextPart
from fastapi.testclient import TestClient

from common.a2a_client import _extract_text, delegate
from registry.__main__ import agents, app


def test_registry_registration_discovery_and_update():
    agents.clear()
    with TestClient(app) as client:
        assert client.get("/discover/tax_question").status_code == 404
        data = {"agent_name": "tax", "tasks": ["tax_question"], "endpoint": "http://127.0.0.1:10102"}
        assert client.post("/register", json=data).status_code == 200
        assert client.get("/discover/tax_question").json()["endpoint"] == data["endpoint"]
        data["endpoint"] = "http://127.0.0.1:20102"
        client.post("/register", json=data)
        assert client.get("/discover/tax_question").json()["endpoint"] == data["endpoint"]
        assert client.get("/health").json()["agent_count"] == 1
    agents.clear()


def test_extract_text_from_sdk_message():
    message = Message(role=Role.agent, message_id="result", parts=[Part(root=TextPart(text="answer"))])
    assert _extract_text(NS(root=NS(result=message))) == "answer"


def test_failed_task_is_not_success():
    with pytest.raises(RuntimeError, match="failed"):
        _extract_text(NS(root=NS(result=NS(status=NS(state="failed")))))


def test_jsonrpc_error_is_not_empty_success():
    with pytest.raises(RuntimeError, match="fixture failure"):
        _extract_text(NS(root=NS(error=NS(message="fixture failure"))))


def test_never_echo_user_history_as_answer():
    result = NS(history=[NS(parts=[NS(text="original user question")])], artifacts=[])
    assert _extract_text(NS(root=NS(result=result))) == ""


@pytest.mark.parametrize("depth", [-1, 4, 100])
async def test_invalid_depth_rejected_before_network(depth):
    with pytest.raises(ValueError, match="depth"):
        await delegate("http://invalid", "question", "context", "trace", depth)
