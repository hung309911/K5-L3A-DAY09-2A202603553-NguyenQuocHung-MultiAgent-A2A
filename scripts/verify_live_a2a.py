"""Verify real LLM-backed A2A, trace, Tax shutdown/recovery, and short Tax prompt.

Uses the shared process manager but launches actual service modules directly,
without tests.service_runner and without patching any model factory.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
from uuid import uuid4

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from common.a2a_client import delegate
from common.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from tax_agent.graph import TAX_SYSTEM_PROMPT
from tests.http_harness import ServiceCluster, free_port


async def main():
    report = {
        "checked_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "provider": os.getenv("LLM_PROVIDER"), "model": os.getenv("GEMINI_MODEL"),
        "uses_test_model": False, "process_bootstrap": "python -m <actual service module>",
        "checks": [], "all_passed": False,
    }
    credentials = [os.getenv(name, "") for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY")]

    def save():
        output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        for key in credentials:
            if key:
                output = output.replace(key, "[REDACTED]")
        (ROOT / "reports" / "live-a2a.json").write_text(output, encoding="utf-8")

    def trace_lines(services, trace, context_id, expected):
        result = {}
        for name, depth in expected.items():
            lines = [line for line in services.read_log(name).splitlines() if "executing |" in line and trace in line]
            if len(lines) != 1 or f"context={context_id}" not in lines[0] or f"depth={depth}" not in lines[0]:
                raise AssertionError(f"Missing or inconsistent trace at {name}")
            result[name] = lines[0]
        return result

    question = (
        "A US company breached a supply contract, deliberately underpaid federal taxes, "
        "and faces SEC compliance reporting failures. Identify the separate tax and "
        "regulatory compliance issues it should investigate. This is a classroom example."
    )
    expected = {"customer_agent": 0, "law_agent": 1, "tax_agent": 2, "compliance_agent": 2}
    save()
    try:
        print("Starting five actual A2A service processes with real Gemini...", flush=True)
        with ServiceCluster(real_llm=True) as services:
            context_id, trace = str(uuid4()), "day9-live-" + str(uuid4())
            print("Checking full Customer -> Law -> Tax + Compliance flow...", flush=True)
            answer = await delegate(services.url("customer_agent"), question, context_id, trace, 0)
            if not answer.strip() or "[FIXTURE:" in answer or "analysis unavailable" in answer.lower():
                raise AssertionError("Full A2A request did not return a complete real response")
            lines = trace_lines(services, trace, context_id, expected)
            report["checks"].append({"check": "full_chain", "passed": True,
                "trace_id": trace, "context_id": context_id, "trace_lines": lines, "answer": answer})
            save()
            print("Full A2A chain: PASS", flush=True)

            print("Stopping Tax Agent, then requesting a partial result...", flush=True)
            old_endpoint = services.url("tax_agent")
            services.stop("tax_agent")
            partial_context, partial_trace = str(uuid4()), "day9-live-tax-down-" + str(uuid4())
            partial = await delegate(services.url("customer_agent"), question, partial_context, partial_trace, 0)
            partial_lines = trace_lines(services, partial_trace, partial_context,
                {"customer_agent": 0, "law_agent": 1, "compliance_agent": 2})
            if not partial.strip() or "call_tax failed" not in services.read_log("law_agent"):
                raise AssertionError("Missing observable Tax failure or partial answer")
            report["checks"].append({"check": "tax_shutdown", "passed": True,
                "trace_lines": partial_lines, "answer": partial,
                "law_log_observation": "call_tax failed; Compliance still executed"})
            save()
            print("Tax shutdown: PASS", flush=True)

            new_port = free_port()
            while new_port in services.ports.values():
                new_port = free_port()
            services.ports["tax_agent"] = new_port
            print("Restarting Tax Agent on a new port and checking discovery...", flush=True)
            services.start("tax_agent", append=True)
            with httpx.Client(trust_env=False) as client:
                info = client.get(services.url("registry") + "/discover/tax_question").json()
            if info["endpoint"] != services.url("tax_agent") or info["endpoint"] == old_endpoint:
                raise AssertionError("Registry did not update the Tax endpoint")
            recovered_context, recovered_trace = str(uuid4()), "day9-live-recovered-" + str(uuid4())
            recovered = await delegate(services.url("customer_agent"), question, recovered_context, recovered_trace, 0)
            recovered_lines = trace_lines(services, recovered_trace, recovered_context, expected)
            if not recovered.strip() or "analysis unavailable" in recovered.lower():
                raise AssertionError("Recovered request is still missing specialist analysis")
            report["checks"].append({"check": "dynamic_rediscovery", "passed": True,
                "old_endpoint": old_endpoint, "new_endpoint": info["endpoint"],
                "trace_lines": recovered_lines, "answer": recovered})
            save()
            print("Tax rediscovery: PASS", flush=True)

            print("Comparing original versus shortened Tax prompt with real LLM...", flush=True)
            tax_question = "For a US corporation, summarize federal tax evasion issues, civil versus criminal exposure, and executive liability."
            original_prompt = TAX_SYSTEM_PROMPT.split("Exercise 5.3:")[0].strip()
            baseline = await get_llm().ainvoke([SystemMessage(content=original_prompt), HumanMessage(content=tax_question)])
            concise = await delegate(services.url("tax_agent"), tax_question, str(uuid4()), "day9-live-tax-short", 0)
            before_words, after_words = len(str(baseline.content).split()), len(concise.split())
            bullets = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", concise))
            prompt_passed = 0 < after_words < 150 and after_words < before_words and bullets <= 4
            report["checks"].append({"check": "shorter_tax_prompt", "passed": prompt_passed,
                "original_prompt_word_count": before_words, "modified_prompt_word_count": after_words,
                "modified_bullet_count": bullets, "original_answer": baseline.content, "modified_answer": concise})
            save()
            if not prompt_passed:
                raise AssertionError(f"Tax prompt length check failed: {before_words} -> {after_words} words, {bullets} bullets")
            print(f"Tax shorter response: PASS ({before_words} -> {after_words} words)", flush=True)
        report["all_passed"] = True
        save()
        print("All real A2A checks passed; service processes stopped.", flush=True)
        return 0
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        save()
        print(f"Live A2A verification failed: {type(exc).__name__}. See reports/live-a2a.json", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
