"""Workflow registry.

This is intentionally tiny: an in-process mapping of names to callables.

It exists to support a simple plugin-style workflow system without introducing
complex frameworks. The public API is exercised by `tests/test_workflow_registry.py`.
"""

from __future__ import annotations

from typing import Any, Callable


_Workflow = Callable[..., Any]


_REGISTRY: dict[str, _Workflow] = {}


def register(name: str, workflow: _Workflow) -> None:
    """Register a workflow under a name.

    Args:
        name: Unique workflow identifier.
        workflow: Callable implementing the workflow.

    Raises:
        ValueError: If name is empty.
    """

    if not name or not name.strip():
        raise ValueError("Workflow name must be non-empty")

    _REGISTRY[name] = workflow


def get(name: str) -> _Workflow:
    """Return the workflow registered under `name`.

    Raises:
        KeyError: If no such workflow exists.
    """

    return _REGISTRY[name]


def clear() -> None:
    """Remove all registered workflows (useful for unit tests)."""

    _REGISTRY.clear()


__all__ = ["register", "get", "clear"]
