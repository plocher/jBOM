"""Workflow layer package.

This package provides lightweight workflow orchestration primitives:
- in-process workflow registry for small extension hooks
- shared adapter-neutral job contracts for request/context/event/result payloads
- a minimal shared job runner used by adapter entry points
"""

from __future__ import annotations

__all__ = ["job_contracts", "job_runner", "registry"]
