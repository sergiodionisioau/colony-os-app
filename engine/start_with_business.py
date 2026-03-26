#!/usr/bin/env python3
"""COE Kernel Startup with Business Module.

Bootstraps the kernel, loads the business module, and starts the API server.
"""

import argparse
import os
import sys
from pathlib import Path


def _import_kernel():
    """Import kernel with path setup."""
    sys.path.insert(0, str(Path(__file__).parent / "coe-kernel"))
    sys.path.insert(0, str(Path(__file__).parent / "modules"))
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
                {"role": "social_agent", "capabilities": ["POST_CREATE", "POST_PUBLISH"]},
                {"role": "business_agent", "capabilities": ["BUSINESS_CRUD", "BUSINESS_METRICS"]}
            ]
        },
        "secrets": {
            "data_path": "/tmp/coe/secrets.json",
            "salt_path": "/tmp/coe/vault.salt",
            "passphrase_env_var": "COE_KERNEL_VAULT_PASSPHRASE"
        },
        "modules": {
            "plugins_dir": str(Path(__file__).parent / "modules"),
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
        "/tmp/coe/keys",
        "/tmp/coe/dlq",
        "/tmp/coe/schemas"
    ]

    for path in paths:
        if path:
            os.makedirs(os.path.dirname(path) if "." in os.path.basename(path) else path, exist_ok=True)


def load_business_module(kernel) -> bool:
    """Load the business module into the kernel."""
    print("\n📦 Loading Business Module...")

    loader = kernel.get_subsystems().get("loader")
    if not loader:
        print("✗ Module loader not available")
        return False

    try:
        # Load business module
        loader.load("business")
        print("✓ Business module loaded successfully")

        # Get module instance and verify health
        instance = loader.get_module_instance("business")
        if instance:
            if hasattr(instance, "healthcheck"):
                health = instance.healthcheck()
                print(f"✓ Business module health: {'HEALTHY' if health else 'UNHEALTHY'}")

                if hasattr(instance, "businesses"):
                    print(f"✓ Loaded {len(instance.businesses)} businesses")
                    for biz_id, biz in instance.businesses.items():
                        print(f"  • {biz.name} ({biz.industry})")

        return True

    except Exception as e:
        print(f"✗ Failed to load business module: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_crm_module(kernel) -> bool:
    """Load the CRM module into the kernel."""
    print("\n📦 Loading CRM Module...")

    loader = kernel.get_subsystems().get("loader")
    if not loader:
        print("✗ Module loader not available")
        return False

    try:
        # Check if CRM module exists
        crm_path = Path(__file__).parent / "modules" / "crm"
        if not crm_path.exists():
            print("⚠ CRM module not found at modules/crm")
            return False

        loader.load("crm")
        print("✓ CRM module loaded successfully")
        return True

    except Exception as e:
        print(f"⚠ Could not load CRM module: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="COE Kernel with Business Module")
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

    print("=" * 70)
    print("🔷 COE Kernel Bootstrap — Business Module Edition")
    print("=" * 70)
    print(f"Mode: {config['bootstrap']['mode']}")
    print(f"API: http://{args.host}:{args.port}")
    print(f"Dashboard: http://{args.host}:{args.port}/")
    print("=" * 70)

    # Initialize kernel
    try:
        kernel = KernelBootstrap(config)
        print("\n✓ Kernel initialized successfully")
        print(f"✓ Audit ledger integrity: {kernel.audit_ledger.verify_integrity()}")
    except Exception as e:
        print(f"\n✗ Kernel initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Load modules
    load_crm_module(kernel)
    load_business_module(kernel)

    # Show loaded modules
    loader = kernel.get_subsystems().get("loader")
    if loader:
        loaded = loader.get_loaded_modules()
        print(f"\n📋 Loaded Modules ({len(loaded)}):")
        for mod_name in loaded:
            instance = loader.get_module_instance(mod_name)
            health = "unknown"
            if instance and hasattr(instance, "healthcheck"):
                try:
                    health = "healthy" if instance.healthcheck() else "unhealthy"
                except Exception:
                    health = "error"
            print(f"  • {mod_name}: {health}")

    # Run health check
    print("\n🏥 Running Health Check...")
    try:
        subsystems = kernel.get_subsystems()
        print(f"  • Event Bus: {'✓' if subsystems.get('bus') else '✗'}")
        print(f"  • Policy Engine: {'✓' if subsystems.get('policy') else '✗'}")
        print(f"  • Audit Ledger: {'✓' if kernel.audit_ledger.verify_integrity() else '✗'}")
        print(f"  • Module Loader: {'✓' if subsystems.get('loader') else '✗'}")
        print(f"  • Connection Pool: {'✓' if subsystems.get('connection_pool') else '✗'}")
        print(f"  • Tool Registry: {'✓' if subsystems.get('tool_registry') else '✗'}")
    except Exception as e:
        print(f"  ⚠ Health check error: {e}")

    # Run API server
    print(f"\n🚀 Starting API server on {args.host}:{args.port}...")
    print("=" * 70)
    print("📊 Dashboard: http://{}:{}/".format(args.host, args.port))
    print("🔍 Health:    http://{}:{}/health-check".format(args.host, args.port))
    print("📡 API:       http://{}:{}/v1/health".format(args.host, args.port))
    print("💼 Business:  http://{}:{}/v1/businesses".format(args.host, args.port))
    print("=" * 70)
    print("Press Ctrl+C to stop\n")

    try:
        kernel.run_api(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        kernel.shutdown()
        print("✓ Goodbye!")


if __name__ == "__main__":
    main()
