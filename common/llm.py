"""Shared OpenAI-compatible factory: OpenRouter or direct Gemini (user requested)."""

import os

from langchain_openai import ChatOpenAI

from common.gemini_chat import GeminiChatOpenAI


def get_llm(temperature: float = 0.3) -> ChatOpenAI:
    """Select provider explicitly, or infer Gemini when only a Google key is set.

    A Google key is sent only to Google's endpoint. OpenRouter remains supported
    for the original codelab. No fixture fallback is used in application code.
    """
    def secret(name: str) -> str:
        value = os.getenv(name, "").strip()
        if value.lower() in {"your_key_here", "your_gemini_key_here", "key_cua_ban"} or value.upper().startswith("YOUR_"):
            return ""
        return value

    router_key = secret("OPENROUTER_API_KEY")
    google_key = secret("GEMINI_API_KEY") or secret("GOOGLE_API_KEY")
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider:
        provider = "gemini" if google_key and not router_key else "openrouter"

    if provider == "gemini":
        api_key = google_key
        model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        required = "GEMINI_API_KEY hoặc GOOGLE_API_KEY"
        # Reserve output tokens for Gemini's thinking and final response.
        provider_options = {"max_tokens": 2000, "reasoning_effort": "minimal"}
        client_type = GeminiChatOpenAI
        # Preserve complete signed tool calls; graph update streaming still works.
        provider_options["disable_streaming"] = True
    elif provider == "openrouter":
        api_key = router_key
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4-5").strip()
        base_url = "https://openrouter.ai/api/v1"
        required = "OPENROUTER_API_KEY"
        provider_options = {"max_tokens": 1000}
        client_type = ChatOpenAI
    else:
        raise ValueError("LLM_PROVIDER phải là openrouter hoặc gemini")

    if not api_key:
        raise ValueError(
            f"Thiếu {required}. Điền key của provider đã chọn vào .env; "
            "hoặc chạy python -m pytest để kiểm tra offline bằng model giả lập."
        )
    if not model:
        raise ValueError("Tên model không được để trống")
    return client_type(
        model=model,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=temperature,
        timeout=60,
        max_retries=2,
        **provider_options,
    )
