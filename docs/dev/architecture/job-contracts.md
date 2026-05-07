# Shared Job Execution Contracts
This document defines the adapter-neutral execution contracts introduced for ADR 0005 Phase 2.
## Purpose
The job contract layer provides one shared execution shape for CLI and future KiCad plugin adapters so orchestration behavior, progress streaming, diagnostics, cancellation semantics, and completion payloads stay consistent across interfaces.
Contract implementation lives in the application layer:
- `src/jbom/application/jobs/contracts.py`
- `src/jbom/application/jobs/runner.py`
The legacy workflow/plugin registry approach (`src/jbom/workflows/registry.py`) is retired and is no longer part of jBOM's runtime architecture.
## Contract types
### `JobRequest`
Represents adapter input translated into orchestration intent:
- `job_type`: stable operation identifier (`bom`, `pos`, etc.)
- `intent`: use-case intent (`generate_bom`, `generate_pos`, etc.)
- `project_ref`: project/session reference supplied by the adapter
- `options`: adapter-sourced execution options normalized for orchestration
- `metadata`: non-domain adapter metadata (for traceability, not business logic)
`JobRequest` is the adapter boundary object and must not carry interface-rendering concerns.
### `JobContext`
Represents runtime context resolved before execution:
- `adapter_id`: caller identity (`cli`, plugin adapter id, etc.)
- `session_id`: adapter session identity
- `capabilities`: runtime capability map (event streaming, cancellation support, etc.)
- `cancellation_requested`: cancellation callback exposed at contract level
This keeps cancellation and runtime capability semantics explicit and interface-independent.
### `JobEvent`
Represents ordered, structured in-flight execution information. Two event kinds are supported:
- `progress`: machine-readable progress payload (`phase`, message, step metadata)
- `diagnostic`: structured diagnostic payload (`severity`, message, code, details)
Event ordering is deterministic (`sequence` monotonic ascending) and is part of the contract, enabling:
- terminal streaming in CLI
- future non-blocking UI rendering in plugin adapters
- stable service-level assertions
### `JobResult`
Represents deterministic completion:
- `outcome`: `succeeded`, `failed`, or `cancelled`
- `artifacts`: typed artifact descriptors emitted by the execution
- `metadata`: completion metadata (including adapter exit mapping fields)
- `events`: full ordered event stream emitted during execution
`JobResult` is the canonical completion contract used by adapters to map orchestration outcome to interface semantics (e.g., process exit codes in CLI, completion notifications in plugin UI).
## Shared runner entry contract
`JobRunner.run(request, context, execute)` is the shared orchestration entry:
1. Emits start progress event.
2. Enforces pre/post cancellation semantics at contract level.
3. Captures structured diagnostics on execution failure.
4. Emits completion event and returns deterministic `JobResult`.
Adapters own rendering and transport of `JobEvent` payloads; the core contract shape remains unchanged across adapters.
