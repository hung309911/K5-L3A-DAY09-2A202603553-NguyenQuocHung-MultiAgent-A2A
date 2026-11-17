"""Run the six codelab entry points with the configured real LLM.

This script makes provider calls and records actual output; it never loads test fixtures.
"""

from datetime import datetime, timedelta, timezone
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINTS = (
    ("stage1", "stages/stage_1_direct_llm/main.py", None),
    ("stage2", "stages/stage_2_rag_tools/main.py", "Tool:"),
    ("exercise2", "exercises/exercise_2_tools.py", "check_statute_of_limitations"),
    ("stage3", "stages/stage_3_single_agent/main.py", "Tool: search_case_law"),
    ("stage4", "stages/stage_4_multi_agent/main.py", "[Node: call_privacy_specialist] Done"),
    ("exercise4", "exercises/exercise_4_multiagent.py", "KẾT QUẢ CUỐI CÙNG"),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true", help="Keep successful entries from the last run")
    args = parser.parse_args()
    config = dotenv_values(ROOT / ".env")
    credentials = [str(config.get(name) or os.getenv(name) or "") for name in (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
    )]

    def redact(text):
        for value in credentials:
            if value:
                text = text.replace(value, "[REDACTED]")
        return text

    reports = ROOT / "reports"
    output_dir = reports / "live-outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "checked_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "provider": config.get("LLM_PROVIDER", "openrouter"),
        "model": config.get("GEMINI_MODEL") if config.get("LLM_PROVIDER") == "gemini" else config.get("OPENROUTER_MODEL"),
        "uses_test_fixtures": False, "entry_points": [], "all_passed": False,
    }
    previous_path = reports / "live-codelab.json"
    if args.resume and previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        if previous.get("provider") == report["provider"] and previous.get("model") == report["model"]:
            report["entry_points"] = [item for item in previous.get("entry_points", []) if item.get("passed")]
    env = os.environ.copy()
    env.update({"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"})
    for name, path, marker in ENTRY_POINTS:
        if any(item["name"] == name for item in report["entry_points"]):
            print(f"{name}: keeping prior successful real-provider result", flush=True)
            continue
        print(f"Running {name} with real LLM...", flush=True)
        started = time.monotonic()
        try:
            result = subprocess.run(
                [sys.executable, path], cwd=ROOT, env=env, capture_output=True,
                encoding="utf-8", errors="replace", timeout=180,
            )
            output = redact(result.stdout + result.stderr)
            passed = result.returncode == 0 and "[FIXTURE:" not in output and (marker is None or marker in output)
            item = {"name": name, "entry_point": path, "exit_code": result.returncode,
                    "passed": passed, "required_output_marker": marker}
        except subprocess.TimeoutExpired as exc:
            output = redact(str(exc.stdout or "") + str(exc.stderr or ""))
            item = {"name": name, "entry_point": path, "passed": False, "error": "Timed out after 180 seconds"}
        item["elapsed_seconds"] = round(time.monotonic() - started, 3)
        output_path = output_dir / f"{name}.txt"
        output_path.write_text(output, encoding="utf-8")
        item["output_file"] = str(output_path.relative_to(ROOT)).replace("\\", "/")
        report["entry_points"].append(item)
        (reports / "live-codelab.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{name}: {'PASS' if item['passed'] else 'FAIL'} ({item['elapsed_seconds']}s)", flush=True)
        if not item["passed"]:
            print(output[-2000:], flush=True)
            return 1
    report["all_passed"] = True
    (reports / "live-codelab.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("All six entry points passed with real provider calls.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
