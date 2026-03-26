#!/usr/bin/env python3
"""COE Kernel Startup Script.

Bootstraps the kernel with REST API and runs the server.
"""

import argparse
import os
import sys
from pathlib import Path


def _import_kernel():
    """Import kernel with path setup."""
    sys.path.insert(0, str(Path(__file__).parent / "coe-kernel"))
    from core.main_enhanced import KernelBootstrap
    return KernelBootstrap


KernelBootstrap = _import_kernel()


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    import yaml

    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        print("Using default configuration...")
        return get_default_config()

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_default_config() -> dict:
    """Return default kernel configuration."""
    return {
        "audit": {
            "storage_path": "/tmp/coe/audit",
            "genesis_constant": "COE_GENESIS_001"
        },
        "bootstrap": {
            "mode": "normal",
            "root_keypair_path": "/tmp/coe/keys/kernel_root.pem",
            "admin_identity": {
                "name": "kernel_admin",
                "role": "admin",
                "type": "user"
            }
        },
        "events": {
            "store_path": "/tmp/coe/events",
            "segment_size": 100000,
            "backpressure_activation_depth": 10000,
            "backpressure_deactivation_depth": 7000
        },
        "rbac": {
            "roles": {
                "admin": ["all"],
                "agent": ["execute_module", "publish_event"],
                "module": ["bus_subscribe", "bus_publish"]
            }
        },
        "policy": {
            "strict_mode": True,
            "agent_scopes": [
                {"role": "revenue_agent", "capabilities": ["SIGNAL_HARVESTING", "EMAIL_OUTREACH"]},
                {"role": "social_agent", "capabilities": ["POST_CREATE", "POST_PUBLISH"]}
            ]
        },
        "secrets": {
            "data_path": "/tmp/coe/secrets.json",
            "salt_path": "/tmp/coe/vault.salt",
            "passphrase_env_var": "COE_KERNEL_VAULT_PASSPHRASE"
        },
        "modules": {
            "plugins_dir": "/tmp/coe/modules",
            "forbidden_imports": [
                "os", "sys", "subprocess", "shutil", "socket",
                "http", "urllib", "ctypes", "importlib",
                "multiprocessing", "signal"
            ]
        },
        "api": {
            "enabled": True,
            "host": "0.0.0.0",
            "port": 8000
        }
    }


def setup_directories(config: dict) -> None:
    """Create necessary directories."""
    paths = [
        config.get("audit", {}).get("storage_path", "/tmp/coe/audit"),
        config.get("events", {}).get("store_path", "/tmp/coe/events"),
        config.get("secrets", {}).get("data_path", "/tmp/coe"),
        config.get("modules", {}).get("plugins_dir", "/tmp/coe/modules"),
        "/tmp/coe/keys",
        "/tmp/coe/dlq",
        "/tmp/coe/schemas"
    ]

    for path in paths:
        if path:
            os.makedirs(os.path.dirname(path) if "." in os.path.basename(path) else path, exist_ok=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="COE Kernel")
    parser.add_argument("--config", "-c", default="config.yaml", help="Configuration file path")
    parser.add_argument("--host", "-H", default="0.0.0.0", help="API server host")
    parser.add_argument("--port", "-p", type=int, default=8000, help="API server port")
    parser.add_argument("--genesis", "-g", action="store_true", help="Run in genesis mode")
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override with command line args
    if args.genesis:
        config["bootstrap"]["mode"] = "genesis"
    config["api"]["host"] = args.host
    config["api"]["port"] = args.port

    # Setup directories
    setup_directories(config)

    print("=" * 60)
    print("COE Kernel Bootstrap")
    print("=" * 60)
    print(f"Mode: {config['bootstrap']['mode']}")
    print(f"API: http://{args.host}:{args.port}")
    print("=" * 60)

    # Initialize kernel
    try:
        kernel = KernelBootstrap(config)
        print("✓ Kernel initialized successfully")
        print(f"✓ Audit ledger: {kernel.audit_ledger.verify_integrity()}")
        print(f"✓ Loaded modules: {kernel.get_subsystems()['loader'].get_loaded_modules()}")
    except Exception as e:
        print(f"✗ Kernel initialization failed: {e}")
        sys.exit(1)

    # Run API server
    print(f"\nStarting API server on {args.host}:{args.port}...")
    print("Press Ctrl+C to stop\n")

    try:
        kernel.run_api(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\nShutting down...")
        kernel.shutdown()
        print("Goodbye!")


if __name__ == "__main__":
    main()
