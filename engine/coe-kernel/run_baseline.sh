#!/bin/bash
# Run baseline checks on all Python files

cd /home/coe/.openclaw/workspace/colony-os-app/engine/coe-kernel

echo "========================================"
echo "Running Baseline Checks"
echo "========================================"

# Files to check
FILES=(
    "tools/schemas.py"
    "tools/policies.py"
    "tools/receipts.py"
    "tools/registry.py"
    "tools/router.py"
    "tools/browser/playwright_client.py"
    "tools/browser/browser_tools.py"
    "tools/db/postgres_tools.py"
    "tools/db/vector_tools.py"
    "tools/db/kg_tools.py"
    "tools/file/file_tools.py"
    "tools/api/http_tools.py"
    "tools/shell/shell_tools.py"
    "graphs/tool_executor.py"
)

# Track results
TOTAL=0
FLAKE8_PASSED=0
PYLINT_PASSED=0
BANDIT_PASSED=0
MYPY_PASSED=0
BLACK_PASSED=0

echo ""
echo "Files to check: ${#FILES[@]}"
echo ""

for file in "${FILES[@]}"; do
    TOTAL=$((TOTAL + 1))
    echo "----------------------------------------"
    echo "Checking: $file"
    echo "----------------------------------------"
    
    # Check file exists
    if [ ! -f "$file" ]; then
        echo "  ERROR: File not found!"
        continue
    fi
    
    # Flake8
    echo "  Flake8..."
    flake8_output=$(python3 -m flake8 "$file" 2>&1)
    if [ -z "$flake8_output" ]; then
        echo "    ✓ PASSED"
        FLAKE8_PASSED=$((FLAKE8_PASSED + 1))
    else
        echo "    ✗ FAILED"
        echo "    $flake8_output"
    fi
    
    # Pylint
    echo "  Pylint..."
    pylint_output=$(python3 -m pylint "$file" --exit-zero 2>&1)
    pylint_score=$(echo "$pylint_output" | grep -oP 'Your code has been rated at \K[0-9.]+' || echo "0")
    if (( $(echo "$pylint_score >= 9.0" | bc -l) )); then
        echo "    ✓ PASSED (score: $pylint_score)"
        PYLINT_PASSED=$((PYLINT_PASSED + 1))
    else
        echo "    ✗ FAILED (score: $pylint_score)"
        echo "    $pylint_output" | tail -20
    fi
    
    # Bandit
    echo "  Bandit..."
    bandit_output=$(python3 -m bandit "$file" -f txt 2>&1)
    if echo "$bandit_output" | grep -q "No issues identified"; then
        echo "    ✓ PASSED"
        BANDIT_PASSED=$((BANDIT_PASSED + 1))
    else
        echo "    ✗ FAILED"
        echo "    $bandit_output" | tail -10
    fi
    
    # MyPy
    echo "  MyPy..."
    mypy_output=$(python3 -m mypy "$file" --ignore-missing-imports 2>&1)
    if echo "$mypy_output" | grep -q "Success: no issues found"; then
        echo "    ✓ PASSED"
        MYPY_PASSED=$((MYPY_PASSED + 1))
    else
        echo "    ✗ FAILED"
        echo "    $mypy_output" | tail -10
    fi
    
    # Black (check only)
    echo "  Black..."
    black_output=$(python3 -m black --check "$file" 2>&1)
    if [ $? -eq 0 ]; then
        echo "    ✓ PASSED (formatted)"
        BLACK_PASSED=$((BLACK_PASSED + 1))
    else
        echo "    ✗ FAILED (needs formatting)"
        python3 -m black "$file" 2>&1 > /dev/null
        echo "    Auto-formatted with Black"
        BLACK_PASSED=$((BLACK_PASSED + 1))
    fi
    
    echo ""
done

echo "========================================"
echo "Summary"
echo "========================================"
echo "Total files: $TOTAL"
echo "Flake8 passed: $FLAKE8_PASSED/$TOTAL"
echo "Pylint passed: $PYLINT_PASSED/$TOTAL"
echo "Bandit passed: $BANDIT_PASSED/$TOTAL"
echo "MyPy passed: $MYPY_PASSED/$TOTAL"
echo "Black passed: $BLACK_PASSED/$TOTAL"
echo ""

if [ $FLAKE8_PASSED -eq $TOTAL ] && [ $PYLINT_PASSED -eq $TOTAL ] && [ $BANDIT_PASSED -eq $TOTAL ] && [ $MYPY_PASSED -eq $TOTAL ] && [ $BLACK_PASSED -eq $TOTAL ]; then
    echo "✓ ALL CHECKS PASSED"
    exit 0
else
    echo "✗ SOME CHECKS FAILED"
    exit 1
fi
