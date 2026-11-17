"""Provider authentication/URL tests never send real credentials or network requests."""

import json

import httpx
from langchain_core.tools import tool
import pytest
from langchain_core.messages import HumanMessage, ToolMessage

from common.llm import get_llm


@pytest.fixture(autouse=True)
def isolated_provider_env(monkeypatch):
    for name in (
        "LLM_PROVIDER", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "GEMINI_API_KEY",
        "GOOGLE_API_KEY", "GEMINI_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("variable", ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
def test_google_key_selects_google_endpoint(monkeypatch, variable):
    monkeypatch.setenv(variable, "fixture-google-key")
    model = get_llm()
    assert model.openai_api_base == "https://generativelanguage.googleapis.com/v1beta/openai/"
    assert model.openai_api_key.get_secret_value() == "fixture-google-key"
    assert model.model_name == "gemini-3.1-flash-lite"


def test_explicit_provider_does_not_mix_credentials(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-google-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fixture-router-key")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "fixture-gemini-model")
    model = get_llm()
    assert model.openai_api_key.get_secret_value() == "fixture-google-key"
    assert model.model_name == "fixture-gemini-model"
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    model = get_llm()
    assert model.openai_api_base == "https://openrouter.ai/api/v1"
    assert model.openai_api_key.get_secret_value() == "fixture-router-key"


def test_google_key_cannot_be_used_as_openrouter_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-google-key")
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        get_llm()


def test_missing_google_key_names_required_setting(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_llm()


def test_unsupported_provider_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "invalid")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        get_llm()


async def test_gemini_tool_call_roundtrip_through_openai_compatibility(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-google-key")

    @tool
    def lookup(query: str) -> str:
        """Look up a teaching example."""
        return query

    request_count = 0

    def handler(request):
        nonlocal request_count
        request_count += 1
        assert request.url.host == "generativelanguage.googleapis.com"
        assert request.url.path == "/v1beta/openai/chat/completions"
        assert request.headers["authorization"] == "Bearer fixture-google-key"
        payload = json.loads(request.content)
        assert payload["tools"][0]["function"]["name"] == "lookup"
        assert payload["model"] == "gemini-3.1-flash-lite"
        if request_count == 2:
            assistant = payload["messages"][1]
            assert assistant["tool_calls"][0]["extra_content"]["google"]["thought_signature"] == "fixture-signature"
            assert payload["messages"][2]["role"] == "tool"
            return httpx.Response(200, json={
                "id": "fixture-final", "object": "chat.completion", "created": 0,
                "model": payload["model"], "choices": [{"index": 0, "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "fixture signed-tool success"}}],
            })
        return httpx.Response(200, json={
            "id": "fixture-google-response", "object": "chat.completion", "created": 0,
            "model": payload["model"], "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                "role": "assistant", "content": None, "tool_calls": [{
                    "id": "fixture-call", "type": "function",
                    "function": {"name": "lookup", "arguments": '{"query":"contract"}'},
                    "extra_content": {"google": {"thought_signature": "fixture-signature"}},
                }],
            }}],
        })

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = get_llm().model_copy(update={"http_async_client": client, "async_client": None, "root_async_client": None})
        # Build a fresh SDK client over the mock transport, without touching a provider.
        from openai import AsyncOpenAI
        sdk = AsyncOpenAI(api_key="fixture-google-key", base_url=model.openai_api_base, http_client=client)
        model.async_client = sdk.chat.completions
        model.root_async_client = sdk
        bound = model.bind_tools([lookup])
        user = HumanMessage(content="Find a contract example")
        response = await bound.ainvoke([user])
        final = await bound.ainvoke([user, response, ToolMessage(content="contract example", tool_call_id="fixture-call")])
    assert response.tool_calls[0]["name"] == "lookup"
    assert response.tool_calls[0]["args"] == {"query": "contract"}
    assert final.content == "fixture signed-tool success"
    assert request_count == 2
