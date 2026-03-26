"""Development utility to sign the CRM module for kernel loading."""

import os
import sys

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# In a real production scenario, the private key would be in a HSM/Vault.
# For this project, we assume the developer has access to the root trust key for local dev.


def sign_module(module_dir: str, private_key_path: str) -> None:
    """Signs the module directory using Ed25519."""
    # Ensure coe-kernel core is discoverable
    sys.path.append(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "coe-kernel"))
    )
    from core.module_loader.signature import compute_module_hash

    # Load private key
    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)

    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise ValueError("Key must be Ed25519")

    # Compute hash and sign
    module_hash = compute_module_hash(module_dir)
    signature = private_key.sign(module_hash)

    # Write signature file
    sig_path = os.path.join(module_dir, "signature.sig")
    with open(sig_path, "wb") as f:
        f.write(signature)
    print(f"Module signed: {sig_path}")


if __name__ == "__main__":
    # Example usage (assuming keys exist in coe-kernel/keys for dev)

    if len(sys.argv) < 3:
        print("Usage: python sign_module.py <module_dir> <private_key_path>")
    else:
        sign_module(sys.argv[1], sys.argv[2])
