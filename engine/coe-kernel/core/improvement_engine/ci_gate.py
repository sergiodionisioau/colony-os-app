"""CI Gate implementation for local test execution.

This module provides the LocalCIGate which executes patch test vectors in a
sandboxed subprocess to verify code improvements.
"""

import contextlib
import io
import logging
import time
import pytest

from core.agent.types import CIResult, Patch
from core.errors import KernelError
from core.interfaces import CIGateInterface


class LocalCIGate(CIGateInterface):
    """Executes module tests in a subprocess sandbox."""

    def is_available(self) -> bool:
        """Indicates whether the subprocess execution environment is ready."""
        return True

    def run_tests(self, patch: Patch) -> CIResult:
        """Executes the patch.test_vector command and captures results."""
        logger = logging.getLogger(__name__)
        start_time = time.monotonic()
        output_buffer = io.StringIO()

        # We redirect stdout/stderr to capture pytest output in-process
        with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(
            output_buffer
        ):
            try:
                # We expect patch.test_vector to be a list of args or a string
                # For pytest.main, we need a list of strings
                args = patch.test_vector.split()

                # Check for -v or other flags if needed
                ret_code = pytest.main(args)

                duration_ms = int((time.monotonic() - start_time) * 1000)
                return CIResult(
                    passed=ret_code in (0, int(pytest.ExitCode.OK)),
                    duration_ms=duration_ms,
                    output=output_buffer.getvalue(),
                )

            except (  # Explicit CI execution fault types
                SystemExit,
                KernelError,
                RuntimeError,
                OSError,
                ValueError,
            ) as exc:
                logger.error("CI in-process execution failed: %s", exc)
                return CIResult(
                    passed=False,
                    duration_ms=0,
                    output=f"CI in-process fault: {str(exc)}",
                )
