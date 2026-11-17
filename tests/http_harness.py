"""Run five real HTTP service processes using the test model bootstrap."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ServiceCluster:
    def __init__(self, *, real_llm=False):
        self.real_llm = real_llm
        self.ports = {}
        for name in ("registry", "tax_agent", "compliance_agent", "law_agent", "customer_agent"):
            port = free_port()
            while port in self.ports.values():
                port = free_port()
            self.ports[name] = port
        self.processes = {}
        self.files = {}
        self.log_dir = ROOT / ".qa" / ("live-a2a" if real_llm else "http")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.evidence = {"model": "real configured provider" if real_llm else "deterministic test fixture; no provider calls", "checks": []}

    def url(self, name):
        return f"http://127.0.0.1:{self.ports[name]}"

    def start(self, name, *, append=False):
        env = os.environ.copy()
        env.update({
            "REGISTRY_URL": self.url("registry"), "SERVER_HOST": "127.0.0.1",
            "REGISTRY_PORT": str(self.ports["registry"]), "AGENT_PORT": str(self.ports[name]),
            "AGENT_ENDPOINT": self.url(name), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1",
            "LANGSMITH_TRACING": "false", "LANGCHAIN_TRACING_V2": "false",
        })
        handle = (self.log_dir / f"{name}.log").open("a" if append else "w", encoding="utf-8")
        self.files[name] = handle
        command = [sys.executable, "-m", name] if self.real_llm else [sys.executable, "-m", "tests.service_runner", name]
        self.processes[name] = subprocess.Popen(
            command, cwd=ROOT, env=env,
            stdout=handle, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        route = "/health" if name == "registry" else "/.well-known/agent-card.json"
        deadline = time.monotonic() + 35
        with httpx.Client(timeout=0.5, trust_env=False) as client:
            while time.monotonic() < deadline:
                if self.processes[name].poll() is not None:
                    raise RuntimeError(f"{name} exited: {self.read_log(name)[-4000:]}")
                try:
                    if client.get(self.url(name) + route).status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
        raise TimeoutError(f"{name} was not ready: {self.read_log(name)[-4000:]}")

    def stop(self, name):
        process = self.processes.pop(name, None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        handle = self.files.pop(name, None)
        if handle:
            handle.close()

    def read_log(self, name):
        return (self.log_dir / f"{name}.log").read_text(encoding="utf-8", errors="replace")

    def __enter__(self):
        try:
            for name in self.ports:
                self.start(name)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *args):
        for name in list(reversed(self.processes)):
            self.stop(name)
