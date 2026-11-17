"""Create a source/report archive using an explicit allowlist; exclude secrets/runtime."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT.parent / "DAY9-MULTI-AGENT-A2A-BAI-LAM.zip"
DIRECTORIES = (
    "common", "registry", "customer_agent", "law_agent", "tax_agent", "compliance_agent",
    "stages", "exercises", "tests", "scripts", "docs", "reports",
)
TOP_FILES = (
    "README.md", "CODELAB.md", "QUICK_REFERENCE.md", "HUONG-DAN.md", "SOURCE.md", "BAO-CAO.md",
    "pyproject.toml", "uv.lock", "constraints.txt", "requirements-dev.txt", "pytest.ini",
    ".env.example", ".gitignore", "test_client.py", "start_all.ps1", "start_all.sh",
)


def include(path):
    return (
        path.is_file()
        and not any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(ROOT).parts)
        and path.suffix.lower() not in {".pyc", ".log", ".zip"}
        and path.name != "SOLUTIONS.md"
    )


if __name__ == "__main__":
    files = [ROOT / name for name in TOP_FILES]
    files += [path for directory in DIRECTORIES for path in (ROOT / directory).rglob("*") if include(path)]
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing submission files: {missing}")
    config = dotenv_values(ROOT / ".env") if (ROOT / ".env").exists() else {}
    secrets = [str(config.get(name) or "").encode("utf-8") for name in (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY",
    ) if config.get(name)]
    for path in files:
        content = path.read_bytes()
        if any(secret in content for secret in secrets):
            raise ValueError(f"Credential found in submission file: {path.relative_to(ROOT)}")
    with ZipFile(TARGET, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, Path("day9-multi-agent") / path.relative_to(ROOT))
    with ZipFile(TARGET) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert not any(part in {".env", ".venv", ".git", ".qa", "__pycache__", "Lab_Assignment"} for name in names for part in Path(name).parts)
    print(f"Created: {TARGET}\nFiles: {len(names)}\nSize: {TARGET.stat().st_size:,} bytes")
