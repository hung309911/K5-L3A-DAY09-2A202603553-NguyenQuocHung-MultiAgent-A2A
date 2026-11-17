"""Make one small real Gemini request and save a credential-free result."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(ROOT / ".env")
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    if not key.strip():
        raise SystemExit("GEMINI_API_KEY is missing from .env")
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    report = {
        "checked_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "provider": "gemini", "model": model, "real_provider_request": True,
        "live_llm_verified": False,
    }
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={"model": model, "max_tokens": 64, "reasoning_effort": "minimal",
                      "messages": [{"role": "user", "content": "Return exactly DAY9_GEMINI_OK. No explanation."}]},
            )
        report["http_status"] = response.status_code
        body = response.json()
        if response.is_success:
            answer = body["choices"][0]["message"].get("content") or ""
            report.update({"answer": answer, "live_llm_verified": "DAY9_GEMINI_OK" in answer,
                           "usage": body.get("usage", {})})
        else:
            error = body.get("error", {})
            report["error"] = {name: error.get(name) for name in ("code", "status", "message")}
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    # Never print or archive the credential, including if a provider echoes it in an error.
    output = json.dumps(report, ensure_ascii=False, indent=2).replace(key, "[REDACTED]") + "\n"
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "gemini-connection.json").write_text(output, encoding="utf-8")
    print(output)
    return 0 if report["live_llm_verified"] else 1


if __name__ == "__main__":
    sys.exit(main())
