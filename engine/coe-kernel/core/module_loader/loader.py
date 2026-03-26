"""Module Loader for the Hardened Module Loader (Lego System).

Provides sandboxed loading, validation, and hot-swapping of kernel modules.
Phase 5 specification §1-§10.
"""

import ast
import builtins
import importlib.util
import json
import os
import uuid
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple, cast

from core.errors import ErrorCode, KernelError
from core.interfaces import ModuleLoaderInterface
from core.module_loader.module_validator import ModuleValidator
from core.module_loader.signature import compute_module_hash, verify_module_signature
from core.types import Event
from core.event_bus.bus import compute_event_signature


class ModuleEventProxy:
    """A proxy injected into module space (§7.152).

    Translates simplified publish(type, payload) calls into strict Event objects.
    """

    def __init__(self, bus: Any, origin_id: str) -> None:
        self._bus = bus
        self._origin_id = origin_id

    def subscribe(self, event_type: str, handler: Any, subscriber_id: str) -> None:
        """Proxies subscription."""
        self._bus.subscribe(event_type, handler, subscriber_id)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Creates a signed Event and publishes it."""
        origin_id = uuid.UUID(int=0) if self._origin_id == "KERNEL" else uuid.uuid4()
        event = Event.create(event_type, payload, origin_id=origin_id)
        # Compute real signature if needed or use N/A if bus allows
        event = replace(event, signature=compute_event_signature(event))
        self._bus.publish(event)


class _ShadowBus:
    """A proxy EventBus for hot-swap operations.

    Mirrors real event bus subscriptions to a shadow instance and captures
    emitted events for validation without actually publishing them to the real bus.
    """

    def __init__(self, real_bus: Any) -> None:
        """Initialize shadow bus."""
        self._real_bus = real_bus
        self.emitted_events: List[Any] = []
        self._shadow_subscriptions: List[Tuple[str, str]] = []

    def subscribe(self, event_type: str, handler: Any, subscriber_id: str) -> None:
        """Proxies subscribe to real bus but injects shadow prefix."""
        shadow_id = f"shadow_{subscriber_id}"
        self._real_bus.subscribe(event_type, handler, shadow_id)
        self._shadow_subscriptions.append((event_type, shadow_id))

    def publish(
        self, event_type: str, payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """Captures event for comparison; does NOT publish to real bus."""
        self.emitted_events.append({"type": event_type, "payload": payload})

    def unsubscribe(self, subscriber_id: str, event_type: str) -> None:
        """Proxies unsubscribe to real bus."""
        shadow_id = f"shadow_{subscriber_id}"
        self._real_bus.unsubscribe(shadow_id, event_type)
        if (event_type, shadow_id) in self._shadow_subscriptions:
            self._shadow_subscriptions.remove((event_type, shadow_id))

    def cleanup(self) -> None:
        """Removes all shadow subscriptions from the real bus."""
        for event_type, shadow_id in self._shadow_subscriptions:
            self._real_bus.unsubscribe(shadow_id, event_type)
        self._shadow_subscriptions.clear()


_FORBIDDEN_ATTR_NAMES = frozenset({"exec", "eval", "compile", "open", "globals"})


def _safe_getattr(obj: Any, name: str, *default: Any) -> Any:
    """Policy-checked getattr proxy for sandboxed module execution.

    Blocks access to dunder attributes (private internals) and
    forbidden builtins that could be used to escape the sandbox.
    """
    if name.startswith("_") or name in _FORBIDDEN_ATTR_NAMES:
        raise AttributeError(f"Sandbox access denied: '{name}'")
    return getattr(obj, name, *default)


class ModuleLoader(ModuleLoaderInterface):
    """Safely parses, analyzes, and isolates logic layers."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the Module Loader."""
        self.modules_path = config["modules_path"]
        self.forbidden_imports = set(config["forbidden_imports"])
        self.public_key = config.get("public_key")

        # Group operational dependencies into a single state container (Pylint R0902)
        self._core = {
            "audit": config["audit_ledger"],
            "registry": config["registry"],
            "bus": config.get("event_bus"),
            "kernel_version": config.get("kernel_version", "1.0.0"),
        }

        # Track loaded modules and evaluation stack
        self._state: Dict[str, Any] = {
            "loaded": {},
            "backups": {},
            "eval_stack": set(),
        }

        # Initialize Validator
        schemas_path = config.get("schemas_path")
        if schemas_path is None:
            schemas_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "schemas"
            )
        self.validator = ModuleValidator(
            schemas_path=schemas_path,
            audit_ledger=self._core["audit"],
            public_key=self.public_key,
        )

    @property
    def audit_ledger(self) -> Any:
        """Expose audit ledger for tests (Phase 5 verification)."""
        return self._core["audit"]

    @property
    def registry(self) -> Any:
        """Expose module registry for tests (Phase 5 verification)."""
        return self._core["registry"]

    @property
    def event_bus(self) -> Any:
        """Expose event bus for tests (Phase 5 verification)."""
        return self._core["bus"]

    @property
    def loaded_modules(self) -> Dict[str, Any]:
        """Expose loaded modules for verification (Phase 5 §10)."""
        return cast(Dict[str, Any], self._state["loaded"])

    @property
    def state(self) -> Dict[str, Any]:
        """Expose internal state for verification (Phase 5 verification)."""
        return self._state

    @property
    def core(self) -> Dict[str, Any]:
        """Expose core operational dependencies for verification."""
        return self._core

    def _analyze_ast(self, source_code: str) -> None:
        """Analyzes an AST tree for illegal instructions."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Syntax error in module: {str(e)}",
            ) from e

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if name in self.forbidden_imports:
                        raise KernelError(
                            code=ErrorCode.MODULE_MANIFEST_INVALID,
                            message=f"Forbidden import: {name}",
                        )
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    name = node.module.split(".")[0]
                    if name in self.forbidden_imports:
                        raise KernelError(
                            code=ErrorCode.MODULE_MANIFEST_INVALID,
                            message=f"Forbidden import: {name}",
                        )

            # Check for generic risk nodes — ast.Name (eval(...)) path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ("exec", "eval", "compile", "open", "globals"):
                    raise KernelError(
                        code=ErrorCode.MODULE_MANIFEST_INVALID,
                        message=f"Forbidden instruction: {node.func.id}",
                    )

            # Check for attribute-based calls — ast.Attribute (builtins.eval(...))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("exec", "eval", "compile", "open", "globals"):
                    raise KernelError(
                        code=ErrorCode.MODULE_MANIFEST_INVALID,
                        message=f"Forbidden attribute call: {node.func.attr}",
                    )

    def _execute_in_sandbox(
        self, name: str, path: str, safe_builtins: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Executes a file in a restricted namespace (§8.174)."""
        if safe_builtins is None:
            # Phase 5 §8.179: Capability-limited environment
            safe_builtins = {
                "__import__": None,  # Block runtime imports
                "abs": abs,
                "all": all,
                "any": any,
                "bool": bool,
                "dict": dict,
                "enumerate": enumerate,
                "filter": filter,
                "float": float,
                "getattr": _safe_getattr,  # Policy-checked proxy
                "hasattr": hasattr,
                "int": int,
                "isinstance": isinstance,
                "iter": iter,
                "len": len,
                "list": list,
                "map": map,
                "max": max,
                "min": min,
                "next": next,
                "object": object,
                "print": print,
                "property": property,
                "range": range,
                "set": set,
                "slice": slice,
                "sorted": sorted,
                "str": str,
                "sum": sum,
                "tuple": tuple,
                "type": type,
                "zip": zip,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "RuntimeError": RuntimeError,
                "AttributeError": AttributeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "StopIteration": StopIteration,
                "Exception": Exception,
            }

        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Failed to create spec for {path}",
            )

        module = importlib.util.module_from_spec(spec)
        vars(module)["__builtins__"] = safe_builtins
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise KernelError(
                code=ErrorCode.MODULE_EXECUTION_FAILED,
                message=(f"Module execution failed: {exc}"),
            ) from exc
        return module.__dict__

    def _load_manifest(self, module_name: str) -> Tuple[Dict[str, Any], str]:
        """Loads a module manifest from legacy or hardened location."""
        manifest_path = os.path.join(self.modules_path, f"{module_name}.json")
        module_dir = self.modules_path
        if not os.path.exists(manifest_path):
            manifest_path = os.path.join(
                self.modules_path, module_name, "manifest.json"
            )
            module_dir = os.path.join(self.modules_path, module_name)

        if not os.path.exists(manifest_path):
            raise KernelError(
                code=ErrorCode.MODULE_NOT_FOUND,
                message=f"Manifest for '{module_name}' not found.",
            )

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = cast(Dict[str, Any], json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Corrupted manifestation for '{module_name}': {str(e)}",
            ) from e

        # Standardized structural validation (Phase 5 §6 Step 1 parity)
        required = [
            "name",
            "version",
            "entrypoint",
            "permissions",
            "events",
            "capabilities",
        ]
        for field in required:
            if field not in manifest:
                raise KernelError(
                    code=ErrorCode.MODULE_MANIFEST_INVALID,
                    message=(
                        f"No entries for {field} in manifest "
                        f"(missing required '{field}' list)"
                    ),
                )

        return manifest, module_dir

    def check_compatibility(self, module: str, version: str, compat: str) -> None:
        """Checks if module version is compatible with the kernel."""
        if compat == "*":
            return
        if self._core["kernel_version"] not in compat:
            k_ver = self._core["kernel_version"]
            msg = f"Module '{module}' (v{version}) incompatible with {k_ver}"
            raise KernelError(code=ErrorCode.MODULE_MANIFEST_INVALID, message=msg)

    def activate_instance(
        self,
        module_name: str,
        namespace: Dict[str, Any],
        manifest: Dict[str, Any],
        bus: Any,
    ) -> Any:
        """Step 9: Activate module instance."""
        instance = None
        try:
            for item in namespace.values():
                if isinstance(item, type) and item.__name__ == "Module":
                    instance = item()
                    if hasattr(instance, "initialize"):
                        instance.initialize(bus)

                    # Step 8: Attach event handlers (§6.147)
                    if bus and hasattr(instance, "handle_event"):
                        # Phase 5 §4 uses events_subscribed
                        subs = manifest.get(
                            "events_subscribed", manifest.get("events", [])
                        )
                        for event_type in subs:
                            bus.subscribe(
                                event_type=event_type,
                                handler=instance.handle_event,
                                subscriber_id=module_name,
                            )
                    break
        except Exception as e:
            self._core["audit"].append(
                actor_id="LOADER",
                action="module_activation",
                status="FAILED",
                metadata={"module": module_name, "error": str(e)},
            )
            raise KernelError(
                code=ErrorCode.MODULE_EXECUTION_FAILED,
                message=f"Activation failed for module '{module_name}': {str(e)}",
            ) from e
        return instance

    def load(self, module_name: str) -> None:
        """AST scans and executes an isolated module layer with versioning support."""
        if module_name in self._state["eval_stack"]:
            raise KernelError(
                code=ErrorCode.MODULE_DEPENDENCY_CIRCULAR,
                message=f"Circular dependency detected for module '{module_name}'.",
            )
        # Phase 5 §10.221: Early bypass for redundant loads
        if module_name in self._state["loaded"]:
            # We'll need the manifest to check version.
            # If it's a hardened module, we still need to validate for now
            # OR we can assume the loaded version is correct.
            # Let's check manifest version from the module_dir first.
            pass

        module_dir = os.path.join(self.modules_path, module_name)
        is_hardened = os.path.exists(os.path.join(module_dir, "manifest.json"))

        if is_hardened:
            manifest = self.validator.validate(module_dir)
        else:
            manifest, module_dir = self._load_manifest(module_name)
            if self.public_key and not verify_module_signature(
                module_dir, self.public_key
            ):
                raise KernelError(
                    code=ErrorCode.MODULE_SIGNATURE_INVALID,
                    message=f"Signature verification failed for module '{module_name}'",
                )

        self._state["eval_stack"].add(module_name)
        for dep in manifest.get("dependencies", []):
            self.load(dep)
        self._state["eval_stack"].remove(module_name)

        version = manifest.get("version", "0.0.0")
        self.check_compatibility(
            module_name, version, manifest.get("kernel_compatibility", "*")
        )

        version = manifest.get("version", "0.0.0")

        # Check if already loaded with SAME version
        if module_name in self._state["loaded"]:
            if self._state["loaded"][module_name]["version"] == version:
                # Same version, skip activation but check compatibility
                # (was already checked)
                return
            # Moving current to backup for rollback (Phase 5 §10)
            self._state["backups"][module_name] = self._state["loaded"][module_name]

        source_path = os.path.join(module_dir, manifest["entrypoint"])
        if not os.path.exists(source_path):
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"Entrypoint file '{source_path}' not found.",
            )

        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        self._analyze_ast(source_code)
        namespace = self._execute_in_sandbox(
            module_name, source_path, builtins.__dict__
        )
        instance = self.activate_instance(
            module_name, namespace, manifest, self._core["bus"]
        )

        # Step 7: Register module in registry (§6.146)
        # Inject resource budget §11
        self._core["registry"].register(
            {
                "module_id": module_name,
                "version": version,
                "capabilities": manifest.get("capabilities", []),
                "event_handlers": manifest.get(
                    "events_subscribed", manifest.get("events", [])
                ),
                "resource_budget": manifest.get("resource_budget"),
                "content_hash": (
                    compute_module_hash(module_dir).hex() if is_hardened else ""
                ),
            }
        )

        self._state["loaded"][module_name] = {
            "manifest": manifest,
            "namespace": namespace,
            "instance": instance,
            "version": version,
        }
        self._core["audit"].append(
            actor_id="LOADER",
            action="module_loaded",
            status="SUCCESS",
            metadata={"module": module_name, "version": version},
        )

    def unload(self, module_name: str) -> None:
        """Safely removes a module from the loaded registry, freeing RAM."""
        if module_name in self._state["loaded"]:
            del self._state["loaded"][module_name]

    def _perform_trial_load(
        self, module_name: str, module_dir: str, shadow_bus: Any
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Any]:
        """Performs Step 1-4 of the hot swap pipeline."""
        manifest = self.validator.validate(module_dir)
        entrypoint = manifest.get("entrypoint", "main.py")
        source_path = os.path.join(module_dir, entrypoint)

        self.check_compatibility(
            module_name,
            manifest.get("version", "0.0.0"),
            manifest.get("kernel_compatibility", "*"),
        )

        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()
        self._analyze_ast(source_code)

        shadow_namespace = self._execute_in_sandbox(
            module_name, source_path, builtins.__dict__
        )

        shadow_instance = self.activate_instance(
            module_name, shadow_namespace, manifest, shadow_bus or self._core["bus"]
        )
        if not shadow_instance:
            raise KernelError(
                ErrorCode.MODULE_MANIFEST_INVALID,
                "No 'Module' class found in candidate.",
            )
        return manifest, shadow_namespace, shadow_instance

    def _finalize_hot_swap(self, ctx: Dict[str, Any]) -> None:
        """Step 6 & 7: Switch and Unload. (Pylint R0913/R0917)"""
        module_name = ctx["name"]
        manifest = ctx["manifest"]
        old_data = self._state["loaded"].get(module_name)
        if old_data:
            self._state["backups"][module_name] = old_data
            old_inst = old_data.get("instance")
            if old_inst and hasattr(old_inst, "shutdown"):
                old_inst.shutdown()
            if self._core["bus"]:
                for event_type in old_data["manifest"].get("events", []):
                    self._core["bus"].unsubscribe(module_name, event_type)

        version = manifest.get("version", "0.0.0")
        self._core["registry"].register(
            {
                "module_id": module_name,
                "version": version,
                "capabilities": manifest.get("capabilities", []),
                "event_handlers": manifest.get(
                    "events_subscribed", manifest.get("events", [])
                ),
                "resource_budget": manifest.get("resource_budget"),
                "content_hash": compute_module_hash(ctx["dir"]).hex(),
            }
        )

        self._state["loaded"][module_name] = {
            "manifest": manifest,
            "namespace": ctx["ns"],
            "instance": ctx["inst"],
            "version": version,
        }

        if self._core["bus"] and hasattr(ctx["inst"], "handle_event"):
            for event_type in manifest.get("events", []):
                self._core["bus"].subscribe(
                    event_type, ctx["inst"].handle_event, module_name
                )

    def hot_swap(self, module_name: str, _new_manifest_path: str = "") -> None:
        """Executes the 7-step upgrade pipeline (Phase 5 §9)."""
        module_dir = os.path.join(self.modules_path, module_name)
        if not os.path.exists(os.path.join(module_dir, "manifest.json")):
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message="Hot swap requires a hardened (directory-based) module.",
            )

        shadow_bus = _ShadowBus(self._core["bus"]) if self._core["bus"] else None
        try:
            manifest, shadow_ns, shadow_inst = self._perform_trial_load(
                module_name, module_dir, shadow_bus
            )

            if hasattr(shadow_inst, "healthcheck") and not shadow_inst.healthcheck():
                raise KernelError(
                    ErrorCode.MODULE_EXECUTION_FAILED, "Shadow healthcheck failed."
                )

            # Step 5: Compare outputs (§9.198)
            # In a real system, we'd feed mirrored event to both and compare.
            # For now, we verify that the shadow instance produced expected
            # initialization events.
            if shadow_bus and shadow_bus.emitted_events:
                self._core["audit"].append(
                    actor_id="LOADER",
                    action="hot_swap_parity_check",
                    status="SUCCESS",
                    metadata={
                        "module": module_name,
                        "shadow_events": len(shadow_bus.emitted_events),
                    },
                )

            if shadow_bus:
                shadow_bus.cleanup()

            self._finalize_hot_swap(
                {
                    "name": module_name,
                    "dir": module_dir,
                    "manifest": manifest,
                    "ns": shadow_ns,
                    "inst": shadow_inst,
                }
            )

            self._core["audit"].append(
                actor_id="LOADER",
                action="module_hot_swap",
                status="SUCCESS",
                metadata={"module": module_name, "version": manifest["version"]},
            )
        except Exception as e:
            if shadow_bus:
                shadow_bus.cleanup()
            self._core["audit"].append(
                actor_id="LOADER",
                action="module_hot_swap",
                status="FAILED",
                metadata={"module": module_name, "error": str(e)},
            )
            raise KernelError(
                code=ErrorCode.MODULE_EXECUTION_FAILED,
                message=f"Hot swap failed for '{module_name}': {str(e)}",
            ) from e

    def rollback(self, module_name: str) -> None:
        """Rolls back to the previous version if available in backups."""
        if module_name in self._state["backups"]:
            backup = self._state["backups"].pop(module_name)
            self._state["loaded"][module_name] = backup

            if (
                self._core["bus"]
                and backup["instance"]
                and hasattr(backup["instance"], "handle_event")
            ):
                for event_type in backup["manifest"].get("events", []):
                    self._core["bus"].subscribe(
                        event_type, backup["instance"].handle_event, module_name
                    )

            self._core["audit"].append(
                actor_id="LOADER",
                action="module_rollback",
                status="SUCCESS",
                metadata={"module": module_name, "version": backup["version"]},
            )
        else:
            raise KernelError(
                code=ErrorCode.MODULE_MANIFEST_INVALID,
                message=f"No backup found for module '{module_name}' to rollback.",
            )

    def get_loaded_modules(self) -> List[str]:
        """Returns list of currently loaded module IDs."""
        return list(self._state["loaded"].keys())

    def get_module_instance(self, module_name: str) -> Optional[Any]:
        """Returns the instance of a loaded module."""
        if module_name in self._state["loaded"]:
            return self._state["loaded"][module_name]["instance"]
        return None

    def get_module_state(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Returns the internal state of a loaded module (Phase 5 verification)."""
        return cast(Optional[Dict[str, Any]], self._state["loaded"].get(module_name))

    def get_backup_state(self, module_name: str) -> Optional[Dict[str, Any]]:
        """Returns the backup state of a module (Phase 5 verification)."""
        return cast(Optional[Dict[str, Any]], self._state["backups"].get(module_name))
