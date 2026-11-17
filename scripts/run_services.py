"""Start the five real services, wait for readiness, and clean up on exit."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    load_dotenv(ROOT / ".env")
    from common.llm import get_llm

    get_llm()  # Validate configuration before launching any process.
    services = [("registry", 10000), ("tax_agent", 10102), ("compliance_agent", 10103), ("law_agent", 10101), ("customer_agent", 10100)]
    # Refuse occupied ports rather than accidentally connecting to another instance.
    for name, port in services:
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError as exc:
                raise RuntimeError(f"Port {port} ({name}) is already in use") from exc
    log_dir = ROOT / ".qa" / "services"
    log_dir.mkdir(parents=True, exist_ok=True)
    children = []
    handles = []
    try:
        for name, port in services:
            handle = (log_dir / f"{name}.log").open("w", encoding="utf-8")
            handles.append(handle)
            env = os.environ.copy()
            env.update({
                "REGISTRY_URL": "http://127.0.0.1:10000", "REGISTRY_PORT": "10000",
                "AGENT_PORT": str(port), "AGENT_ENDPOINT": f"http://127.0.0.1:{port}",
                "SERVER_HOST": "127.0.0.1", "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1",
            })
            process = subprocess.Popen(
                [sys.executable, "-m", name], cwd=ROOT, env=env,
                stdout=handle, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            children.append(process)
            path = "/health" if name == "registry" else "/.well-known/agent-card.json"
            deadline = time.monotonic() + 45
            with httpx.Client(timeout=1, trust_env=False) as client:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} exited; read {log_dir / (name + '.log')}")
                    try:
                        if client.get(f"http://127.0.0.1:{port}{path}").status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if time.monotonic() >= deadline:
                        raise TimeoutError(f"{name} did not become ready; see {log_dir}")
                    time.sleep(0.2)
            print(f"Ready: {name} http://127.0.0.1:{port}", flush=True)
        print("Send a question: python test_client.py\nPress Ctrl+C to stop. Logs: .qa/services", flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(0.5)
        raise RuntimeError("A service stopped unexpectedly; see .qa/services")
    except KeyboardInterrupt:
        print("Stopping services...", flush=True)
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
