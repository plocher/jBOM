"""Shared job runner for adapter-neutral orchestration flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from jbom.application.jobs.contracts import (
    JobArtifact,
    JobContext,
    JobDiagnostic,
    JobDiagnosticSeverity,
    JobEvent,
    JobEventKind,
    JobOutcome,
    JobProgress,
    JobRequest,
    JobResult,
)

Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    """Return timezone-aware current UTC time."""

    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class JobRunPayload:
    """Adapter callback payload consumed by the shared `JobRunner`."""

    outcome: JobOutcome = JobOutcome.SUCCEEDED
    artifacts: tuple[JobArtifact, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "metadata", dict(self.metadata))


class JobEventStream:
    """Mutable event stream used during one in-process job execution."""

    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock
        self._next_sequence = 1
        self._events: list[JobEvent] = []

    def progress(
        self,
        *,
        phase: str,
        message: str,
        step_index: int | None = None,
        step_count: int | None = None,
        percent: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Append a progress event to the ordered stream."""

        self._append(
            JobEvent(
                sequence=self._next_sequence,
                occurred_at_utc=self._clock(),
                kind=JobEventKind.PROGRESS,
                progress=JobProgress(
                    phase=phase,
                    message=message,
                    step_index=step_index,
                    step_count=step_count,
                    percent=percent,
                    metadata=metadata or {},
                ),
            )
        )

    def diagnostic(
        self,
        *,
        severity: JobDiagnosticSeverity,
        message: str,
        code: str = "",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        """Append a diagnostic event to the ordered stream."""

        self._append(
            JobEvent(
                sequence=self._next_sequence,
                occurred_at_utc=self._clock(),
                kind=JobEventKind.DIAGNOSTIC,
                diagnostic=JobDiagnostic(
                    severity=severity,
                    message=message,
                    code=code,
                    details=details or {},
                ),
            )
        )

    @property
    def events(self) -> tuple[JobEvent, ...]:
        """Return immutable ordered event tuples."""

        return tuple(self._events)

    def _append(self, event: JobEvent) -> None:
        """Append one pre-built event while maintaining monotonic sequence values."""

        self._events.append(event)
        self._next_sequence += 1


class JobRunner:
    """Execute one job request through a shared event-emitting contract."""

    def __init__(self, *, clock: Clock = _utc_now) -> None:
        self._clock = clock

    def run(
        self,
        *,
        request: JobRequest,
        context: JobContext,
        execute: Callable[[JobEventStream], JobRunPayload],
    ) -> JobResult:
        """Execute a job callback and return a deterministic contract payload."""

        events = JobEventStream(clock=self._clock)
        events.progress(
            phase="start",
            message=f"Starting {request.job_type} job",
        )

        if context.cancellation_requested():
            events.diagnostic(
                severity=JobDiagnosticSeverity.WARNING,
                message="Job cancelled before execution",
                code="job_cancelled",
            )
            return JobResult(
                request=request,
                context=context,
                outcome=JobOutcome.CANCELLED,
                metadata={"cancelled": True},
                events=events.events,
            )

        try:
            payload = execute(events)
        except Exception as exc:  # pragma: no cover - defensive safety path
            events.diagnostic(
                severity=JobDiagnosticSeverity.ERROR,
                message=str(exc),
                code="job_execution_error",
            )
            return JobResult(
                request=request,
                context=context,
                outcome=JobOutcome.FAILED,
                metadata={"error": str(exc), "cancelled": False},
                events=events.events,
            )

        if context.cancellation_requested():
            events.diagnostic(
                severity=JobDiagnosticSeverity.WARNING,
                message="Job cancelled during execution",
                code="job_cancelled",
            )
            metadata = dict(payload.metadata)
            metadata["cancelled"] = True
            return JobResult(
                request=request,
                context=context,
                outcome=JobOutcome.CANCELLED,
                artifacts=payload.artifacts,
                metadata=metadata,
                events=events.events,
            )

        if payload.outcome == JobOutcome.SUCCEEDED:
            events.progress(
                phase="complete",
                message=f"Completed {request.job_type} job",
            )
        elif payload.outcome == JobOutcome.FAILED:
            events.diagnostic(
                severity=JobDiagnosticSeverity.ERROR,
                message=f"{request.job_type} job completed with failure outcome",
                code="job_failed",
            )
        else:
            events.diagnostic(
                severity=JobDiagnosticSeverity.WARNING,
                message=f"{request.job_type} job completed with cancellation outcome",
                code="job_cancelled",
            )

        metadata = dict(payload.metadata)
        metadata.setdefault("cancelled", payload.outcome == JobOutcome.CANCELLED)
        return JobResult(
            request=request,
            context=context,
            outcome=payload.outcome,
            artifacts=payload.artifacts,
            metadata=metadata,
            events=events.events,
        )


__all__ = [
    "JobEventStream",
    "JobRunPayload",
    "JobRunner",
]
