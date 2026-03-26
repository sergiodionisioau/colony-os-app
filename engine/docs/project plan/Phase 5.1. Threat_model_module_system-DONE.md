# Threat Model: Hardened Module System (Phase 5)

## 1. Introduction
The Hardened Module System (Lego System) is designed to allow external, untrusted modules to run within the CoE Operating System without compromising the kernel or other modules. This document outlines the security architecture, trust boundaries, and mitigation strategies for identified threats.

## 2. Trust Boundaries
- **Kernel Space**: Fully trusted. Contains the Policy Engine, Audit Ledger, and Entry Bus.
- **Module Space**: Untrusted/Low Trust. Each module is isolated in its own sandbox.
- **Persistence Layer**: Trusted (Encrypted). Where module artifacts and registries are stored.

## 3. Attack Vectors & Mitigations

| Threat | Description | MITRE ATT&CK | Security Control |
| :--- | :--- | :--- | :--- |
| **Privilege Escalation** | A module attempts to call kernel-level functions or access reserved memory. | T1068 | **AST Scanning** identifies and rejects forbidden calls ([exec](file:///c:/Users/sergi/colony/backend/col/engine/coe-kernel/core/agent/orchestrator.py#85-171), [eval](file:///c:/Users/sergi/colony/backend/col/engine/coe-kernel/core/agent/scope_enforcer.py#55-89), restricted imports). |
| **Signature Forgery** | An attacker provides a malicious module with a fake signature. | T1581 | **Ed25519 Signatures** verified against vendor public keys before loading. |
| **Resource Exhaustion** | A module consumes excessive CPU or memory to DOS the kernel. | T1499 | **Resource Budgets** (CPU, RAM, Event limits) enforced by Policy Engine. |
| **Data Exfiltration** | A module tries to send data to an external network without permission. | T1041 | **Capability Masking**: Modules only have access to permitted handlers and the Event Bus. |
| **Lateral Movement** | A module attempts to call another module's private functions directly. | T1210 | **Logical Isolation**: Modules can only communicate via the Event Bus. Direct memory access is blocked by namespace isolation. |
| **Malicious Registry Mutation** | A module tries to alter its own status or capabilities in the registry. | T1036 | **Strict Typing**: Registry entries are immutable to modules and managed solely by the Loader. |

## 4. Secure Loading Pipeline
To ensure integrity, every module must pass a 10-step zero-trust pipeline:
1. **Structure Audit**: Verify all required artifacts (`manifest.json`, `signature.sig`, etc.) exist.
2. **Schema Sanitization**: Manifest must conform to the strict JSON schema.
3. **Capability Binding**: Map requested capabilities against the system whitelist.
4. **Signature Verification**: Crypographic check of the entire module directory.
5. **AST Analysis**: Deep inspection of source code for illegal instructions.
6. **Sandbox Initialization**: Create a restricted execution namespace.
7. **Namespace Binding**: Inject only permitted builtins and event proxies.
8. **Lifecycle Activation**: Initialize the module and attach handlers.
9. **Registry Entry**: Log the module version, hash, and status.
10. **Audit Seal**: Write a non-repudiable audit entry to the ledger.

## 5. Hot-Swap Invariants
- **Shadow Loading**: New versions are loaded in a mirror environment for testing.
- **No-Gap Subscriptions**: Real-time event routing is transferred without loss.
- **Rollback Guarantee**: Previous stable state is preserved in memory for immediate recovery.

## 6. Security Assumptions
- The **Public Key** for signature verification is provided via a secure, authenticated channel.
- The **Host OS** provides basic file system isolation and process stability.
- The **Policy Engine** is correctly configured to enforce the budgets declared in module manifests.
