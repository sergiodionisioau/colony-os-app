"""Tests for module signature verification logic.

Verifies SHA-256 hashing of directory contents and Ed25519 signature validation.
"""

import os
import tempfile
from typing import Any, cast

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from core.errors import KernelError
from core.module_loader.signature import compute_module_hash, verify_module_signature


def test_signature_verification_flow() -> None:
    """Verifies that a correctly signed module passes and tampered one fails."""
    # 1. Setup keys
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=cast(Any, Encoding.Raw), format=cast(Any, PublicFormat.Raw)
    )

    with tempfile.TemporaryDirectory() as td:
        # 2. Create module files
        with open(os.path.join(td, "manifest.json"), "w", encoding="utf-8") as f:
            f.write('{"name": "test_module"}')
        with open(os.path.join(td, "main.py"), "w", encoding="utf-8") as f:
            f.write('print("hello")')

        # 3. Compute hash and sign
        module_hash = compute_module_hash(td)
        signature = private_key.sign(module_hash)

        with open(os.path.join(td, "signature.sig"), "wb") as f:
            f.write(signature)

        # 4. Verify - Success
        assert verify_module_signature(td, public_key_bytes) is True

        # 5. Tamper with file - Failure
        with open(os.path.join(td, "main.py"), "w", encoding="utf-8") as f:
            f.write('print("evil")')
        assert verify_module_signature(td, public_key_bytes) is False

        # 6. Restore file - Success
        with open(os.path.join(td, "main.py"), "w", encoding="utf-8") as f:
            f.write('print("hello")')
        assert verify_module_signature(td, public_key_bytes) is True

        # 7. Add new file - Failure
        with open(os.path.join(td, "extra.py"), "w", encoding="utf-8") as f:
            f.write('print("extra")')
        assert verify_module_signature(td, public_key_bytes) is False


def test_missing_signature_raises_error() -> None:
    """Verifies that missing signature.sig raised KernelError."""
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w", encoding="utf-8") as f:
            f.write('print("hello")')

        try:
            verify_module_signature(td, b"dummy_pubkey")
            assert False, "Should have raised KernelError"
        except KernelError as e:
            assert "Missing signature.sig" in e.message
