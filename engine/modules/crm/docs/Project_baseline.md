## 🛑 Zero Tolerance Baseline (Global)

System build or verification FAILS if:
1. **Implicit Permissions:** Any capability executes without an explicit policy "ALLOW".
2. **Hidden State:** AI providers or modules store state outside kernel-managed channels.
3. **Non-Determinism:** Identical seeds/inputs produce different audit trails.
4. **Audit Bypass:** Any state mutation occurs without a corresponding hash-chained audit entry.
5. **Privilege Escalation:** Any identity (user/agent) can elevate roles without an audited parent authorization.

Explicitly reject any build or verification attempt that fails to meet these criteria. 

0 errors = Pass
1+ errors = Fail

0 Test suite failures = Pass
1+ Test suite failures = Fail

0 violations = Pass
1+ violations = Fail

0 warnings = Pass
1+ warnings = Fail

0 suspensions = Pass
1+ suspensions = Fail

0 runtime exceptions = Pass
1+ runtime exceptions = Fail

Baseline MUST pass all: Flake8, Ruff, Black, Pylint, MyPy, Bandit, Vulture, Pyright, Coverage.py, PipAudit, Vulture, Semgrep

0 violations = Pass
1+ violations = Fail

0 Test suite failures = Pass
1+ Test suite failures = Fail

0 linting errors = Pass
1+ linting errors = Fail

0 type errors = Pass
1+ type errors = Fail

0 security vulnerabilities = Pass
1+ security vulnerabilities = Fail

0 test failures = Pass
1+ test failures = Fail

0 violations = Pass
1+ violations = Fail

0 warnings = Pass
1+ warnings = Fail

0 suspensions = Pass
1+ suspensions = Fail

0 runtime exceptions = Pass
1+ runtime exceptions = Fail

0 Silent failures = Pass
1+ Silent failures = Fail

Project MUST pass all unit tests before proceeding to the next phase and happy path tests.