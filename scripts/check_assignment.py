"""Reproduce offline tests and save actual evidence for the hand-in."""

from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
reports = ROOT / "reports"
reports.mkdir(exist_ok=True)
env = os.environ.copy()
env.update({"PYTHONUTF8": "1", "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false"})
result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "--junitxml=reports/test-results.xml"],
    cwd=ROOT, env=env, capture_output=True, encoding="utf-8", errors="replace",
)
output = result.stdout + result.stderr
(reports / "test-output.txt").write_text(output, encoding="utf-8")
print(output)
summary = {
    "checked_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
    "python": platform.python_version(), "platform": platform.platform(),
    "command": "python -m pytest -q --junitxml=reports/test-results.xml",
    "exit_code": result.returncode,
    "llm_provider_calls": False,
    "live_llm_verified": False,
    "official_grading_suite": False,
    "test_model": "tests.fake_llm.FixtureChatModel (orchestration only)",
    "versions": {name: version(name) for name in ("langgraph", "langchain-core", "langchain-openai", "langsmith", "a2a-sdk", "pytest")},
}
(reports / "verification.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
sys.exit(result.returncode)
