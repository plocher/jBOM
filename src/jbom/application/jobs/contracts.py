"""Shared adapter-neutral job execution contracts.

This module provides typed contracts for orchestration requests, runtime context,
structured progress/diagnostic events, and deterministic completion payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Mapping


def _freeze_mapping(values: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return an immutable copy of a metadata/options mapping."""

    return MappingProxyType(dict(values or {}))


def _validate_non_empty(value: str, *, field_name: str) -> str:
    """Validate and normalize a required non-empty text field."""

    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    return normalized


def _never_cancelled() -> bool:
    """Default cancellation callback for non-cancellable contexts."""

    return False


class JobOutcome(str, Enum):
    """Terminal outcome state for one job execution."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobEventKind(str, Enum):
    """Supported event payload types."""

    PROGRESS = "progress"
    DIAGNOSTIC = "diagnostic"


class JobDiagnosticSeverity(str, Enum):
    """Severity levels for diagnostic event payloads."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class JobRequest:
    """Execution intent and options for one job."""

    job_type: str
    intent: str
    project_ref: str
    options: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "job_type", _validate_non_empty(self.job_type, field_name="job_type")
        )
        object.__setattr__(
            self, "intent", _validate_non_empty(self.intent, field_name="intent")
        )
        object.__setattr__(
            self,
            "project_ref",
            _validate_non_empty(self.project_ref, field_name="project_ref"),
        )
        object.__setattr__(self, "options", _freeze_mapping(self.options))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class JobContext:
    """Runtime context resolved by an adapter before execution begins."""

    adapter_id: str
    session_id: str
    capabilities: Mapping[str, Any] = field(default_factory=dict)
    cancellation_requested: Callable[[], bool] = field(
        default=_never_cancelled,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "adapter_id",
            _validate_non_empty(self.adapter_id, field_name="adapter_id"),
        )
        object.__setattr__(
            self,
            "session_id",
            _validate_non_empty(self.session_id, field_name="session_id"),
        )
        object.__setattr__(self, "capabilities", _freeze_mapping(self.capabilities))


@dataclass(frozen=True)
class JobProgress:
    """Progress payload for `JobEventKind.PROGRESS` events."""

    phase: str
    message: str
    step_index: int | None = None
    step_count: int | None = None
    percent: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "phase", _validate_non_empty(self.phase, field_name="phase")
        )
        object.__setattr__(
            self, "message", _validate_non_empty(self.message, field_name="message")
        )
        if self.step_index is not None and self.step_index < 0:
            raise ValueError("step_index must be >= 0")
        if self.step_count is not None and self.step_count < 0:
            raise ValueError("step_count must be >= 0")
        if (
            self.step_index is not None
            and self.step_count is not None
            and self.step_index > self.step_count
        ):
            raise ValueError("step_index cannot exceed step_count")
        if self.percent is not None and not (0.0 <= self.percent <= 100.0):
            raise ValueError("percent must be between 0 and 100")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class JobDiagnostic:
    """Diagnostic payload for `JobEventKind.DIAGNOSTIC` events."""

    severity: JobDiagnosticSeverity
    message: str
    code: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "message", _validate_non_empty(self.message, field_name="message")
        )
        object.__setattr__(self, "code", str(self.code or "").strip())
        object.__setattr__(self, "details", _freeze_mapping(self.details))


@dataclass(frozen=True)
class JobEvent:
    """One ordered event emitted during job execution."""

    sequence: int
    occurred_at_utc: datetime
    kind: JobEventKind
    progress: JobProgress | None = None
    diagnostic: JobDiagnostic | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("sequence must be > 0")
        if self.occurred_at_utc.tzinfo is None:
            raise ValueError("occurred_at_utc must be timezone-aware")
        object.__setattr__(
            self,
            "occurred_at_utc",
            self.occurred_at_utc.astimezone(timezone.utc),
        )
        if self.kind == JobEventKind.PROGRESS:
            if self.progress is None or self.diagnostic is not None:
                raise ValueError("Progress events require progress payload only")
        elif self.kind == JobEventKind.DIAGNOSTIC:
            if self.diagnostic is None or self.progress is not None:
                raise ValueError("Diagnostic events require diagnostic payload only")
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class JobArtifact:
    """Deterministic artifact descriptor emitted by a completed job."""

    name: str
    location: str
    media_type: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "name", _validate_non_empty(self.name, field_name="name")
        )
        object.__setattr__(
            self, "location", _validate_non_empty(self.location, field_name="location")
        )
        object.__setattr__(
            self,
            "media_type",
            _validate_non_empty(self.media_type, field_name="media_type"),
        )
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))


@dataclass(frozen=True)
class JobResult:
    """Deterministic completion payload containing outcome, artifacts, and events."""

    request: JobRequest
    context: JobContext
    outcome: JobOutcome
    artifacts: tuple[JobArtifact, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    events: tuple[JobEvent, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata))
        previous_sequence = 0
        for event in self.events:
            if event.sequence <= previous_sequence:
                raise ValueError("Job events must be strictly ordered by sequence")
            previous_sequence = event.sequence


__all__ = [
    "JobArtifact",
    "JobContext",
    "JobDiagnostic",
    "JobDiagnosticSeverity",
    "JobEvent",
    "JobEventKind",
    "JobOutcome",
    "JobProgress",
    "JobRequest",
    "JobResult",
]
