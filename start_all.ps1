# Python owns child processes and cleans up on Ctrl+C.
$ErrorActionPreference = 'Stop'
$taskPythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $taskPythonPath) {
    & $taskPythonPath (Join-Path $PSScriptRoot 'scripts/run_services.py')
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    Push-Location $PSScriptRoot
    try { & uv run python scripts/run_services.py } finally { Pop-Location }
} else {
    throw 'Create .venv and install requirements-dev.txt first; see HUONG-DAN.md.'
}
exit $LASTEXITCODE
