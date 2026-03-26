"""Module signature verification using SHA-256 and Ed25519."""

import hashlib
import os
from typing import List
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from core.errors import ErrorCode, KernelError


def compute_module_hash(module_path: str) -> bytes:
    """Computes a combined SHA-256 hash of all files in the module directory.

    Excludes 'signature.sig' to avoid circular dependency.
    Files are processed in alphabetical order for determinism.
    """
    hasher = hashlib.sha256()

    # Get all files recursively, excluding signature.sig
    all_files: List[str] = []
    for root, dirs, files in os.walk(module_path):
        # Exclude __pycache__ from search
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")

        for file in files:
            if file == "signature.sig" or file.startswith("."):
                continue
            full_path = os.path.join(root, file)
            all_files.append(full_path)

    all_files.sort()

    for file_path in all_files:
        # Include relative path in hash to detect file moves/renames
        rel_path = os.path.relpath(file_path, module_path)
        hasher.update(rel_path.encode())

        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)

    return hasher.digest()


def verify_module_signature(module_path: str, public_key_bytes: bytes) -> bool:
    """Verifies the 'signature.sig' file against the module directory contents.

    Uses Ed25519 for modern, robust verification.
    """
    sig_path = os.path.join(module_path, "signature.sig")
    if not os.path.exists(sig_path):
        raise KernelError(
            code=ErrorCode.MODULE_SIGNATURE_INVALID,
            message=f"Missing signature.sig in module {module_path}",
        )

    try:
        with open(sig_path, "rb") as f:
            signature = f.read()

        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        module_hash = compute_module_hash(module_path)

        public_key.verify(signature, module_hash)
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        raise KernelError(
            code=ErrorCode.UNKNOWN_FAULT,
            message=f"Signature verification failed: {str(e)}",
        ) from e
