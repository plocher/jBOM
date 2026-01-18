"""Minimal workflow registry.

Workflows are callables registered by name so CLI and other callers can
invoke them without coupling to concrete service implementations.
"""
from __future__ import annotations

from typing import Callable, Dict


_REGISTRY: Dict[str, Callable[..., object]] = {}


def register(name: str, func: Callable[..., object]) -> None:
    if not name or not callable(func):
        raise ValueError("Invalid workflow registration")
    _REGISTRY[name] = func


def get(name: str) -> Callable[..., object]:
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"Workflow not found: {name}") from e


def clear() -> None:
    _REGISTRY.clear()
