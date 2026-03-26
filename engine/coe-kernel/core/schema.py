"""JSON Schema definition for the COE Kernel configuration."""

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "bootstrap": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["genesis", "normal"]},
                "root_keypair_path": {"type": "string"},
                "admin_identity": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "role": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["name", "role"],
                },
            },
            "required": ["mode"],
        },
        "audit": {
            "type": "object",
            "properties": {
                "storage_path": {"type": "string"},
                "genesis_constant": {"type": "string"},
                "hash_algorithm": {"type": "string"},
            },
        },
        "secrets": {
            "type": "object",
            "properties": {
                "passphrase_env_var": {"type": "string"},
                "passphrase": {"type": "string"},
                "salt_path": {"type": "string"},
                "data_path": {"type": "string"},
            },
        },
        "rbac": {
            "type": "object",
            "properties": {
                "roles": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                }
            },
        },
        "policy": {
            "type": "object",
            "properties": {
                "rules_path": {"type": "string"},
                "strict_mode": {"type": "boolean"},
            },
        },
        "events": {
            "type": "object",
            "properties": {
                "schema_path": {"type": "string"},
                "store_path": {"type": "string"},
                "dlq_path": {"type": "string"},
                "timeout": {"type": "integer", "minimum": 0},
                "max_events": {"type": "integer", "minimum": 1},
                "retention_policy": {"type": "string"},
                "segment_size": {"type": "integer", "minimum": 1},
                "archive_segments": {"type": "boolean"},
                "archive_path": {"type": "string"},
                "backpressure_activation_depth": {"type": "integer", "minimum": 1},
                "backpressure_deactivation_depth": {"type": "integer", "minimum": 1},
            },
        },
        "modules": {
            "type": "object",
            "properties": {
                "plugins_dir": {"type": "string"},
                "forbidden_imports": {"type": "array", "items": {"type": "string"}},
                "max_load_retries": {"type": "integer", "minimum": 0},
                "healthcheck_interval_seconds": {"type": "integer", "minimum": 1},
                "max_unhealthy_checks": {"type": "integer", "minimum": 1},
            },
        },
    },
    "required": ["bootstrap"],
}
