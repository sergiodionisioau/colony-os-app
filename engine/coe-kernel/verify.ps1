# COE Kernel Verification Script
# This strict script acts as the absolute quality gate.
# A single linter warning, type mismatch, or test failure will stop the build.

$ErrorActionPreference = "Stop"

Write-Host "--- Running Black (Formatting Check) ---" -ForegroundColor Cyan
black --check core tests
if ($LASTEXITCODE -ne 0) { Write-Host "Black formatting failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running Flake8 (Style Enforcement) ---" -ForegroundColor Cyan
flake8 core tests
if ($LASTEXITCODE -ne 0) { Write-Host "Flake8 style enforcement failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running Pylint (Code Quality) ---" -ForegroundColor Cyan
pylint core tests
if ($LASTEXITCODE -ne 0) { Write-Host "Pylint code quality gate failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running MyPy (Type Checking) ---" -ForegroundColor Cyan
mypy core tests --strict
if ($LASTEXITCODE -ne 0) { Write-Host "MyPy strict typing failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running Pyright (Advanced Typing) ---" -ForegroundColor Cyan
pyright core tests
if ($LASTEXITCODE -ne 0) { Write-Host "Pyright typing failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running Bandit (Security Scan) ---" -ForegroundColor Cyan
bandit -r core
if ($LASTEXITCODE -ne 0) { Write-Host "Bandit security scan failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running Pip-Audit (Security Scan) ---" -ForegroundColor Cyan
pip-audit
if ($LASTEXITCODE -ne 0) { Write-Host "Pip-Audit security scan failed!" -ForegroundColor Red; exit 1 }

Write-Host "--- Running Pytest & Coverage (Test Execution) ---" -ForegroundColor Cyan
pytest tests -v --cov=core --cov-report=term-missing --cov-fail-under=100
if ($LASTEXITCODE -ne 0) { Write-Host "Pytest suite or coverage gate failed!" -ForegroundColor Red; exit 1 }

Write-Host "ALL QUALITY GATES PASSED. ZERO TOLERANCE MET." -ForegroundColor Green
exit 0
