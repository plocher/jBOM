"""Service-level contract tests for shared job execution semantics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

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
from jbom.application.jobs.runner import JobRunPayload, JobRunner


class _TickingClock:
    """Deterministic UTC clock for event timestamp assertions."""

    def __init__(self, start: datetime) -> None:
        self._next_value = start

    def __call__(self) -> datetime:
        current = self._next_value
        self._next_value = self._next_value + timedelta(seconds=1)
        return current


def _make_request() -> JobRequest:
    """Create a valid request fixture used across tests."""

    return JobRequest(
        job_type="bom",
        intent="generate_bom",
        project_ref="demo-project",
        options={"fabricator": "generic"},
    )


def _make_context(*, cancellation_requested=None) -> JobContext:
    """Create a valid context fixture used across tests."""

    if cancellation_requested is None:

        def _not_cancelled() -> bool:
            return False

        cancellation_requested = _not_cancelled

    return JobContext(
        adapter_id="cli",
        session_id="session-1",
        capabilities={"event_stream": True},
        cancellation_requested=cancellation_requested,
    )


def _run_success_job(*, clock_start: datetime) -> JobResult:
    """Run one successful job execution with deterministic event emissions."""

    runner = JobRunner(clock=_TickingClock(clock_start))
    request = _make_request()
    context = _make_context()

    def _execute(events) -> JobRunPayload:
        events.progress(
            phase="load",
            message="Loading project context",
            step_index=1,
            step_count=2,
        )
        events.progress(
            phase="emit",
            message="Rendering BOM output",
            step_index=2,
            step_count=2,
        )
        return JobRunPayload(
            artifacts=(
                JobArtifact(
                    name="bom.csv",
                    location="project-default://bom.csv",
                    media_type="text/csv",
                ),
            ),
            metadata={"exit_code": 0},
            outcome=JobOutcome.SUCCEEDED,
        )

    return runner.run(request=request, context=context, execute=_execute)


def test_job_runner_produces_deterministic_results_for_same_inputs() -> None:
    """Runner output should be stable for equivalent request/context/payload inputs."""

    start = datetime(2026, 5, 1, tzinfo=timezone.utc)
    first = _run_success_job(clock_start=start)
    second = _run_success_job(clock_start=start)

    assert first.outcome == JobOutcome.SUCCEEDED
    assert second.outcome == JobOutcome.SUCCEEDED
    assert first.events == second.events
    assert first.artifacts == second.artifacts
    assert first.metadata == second.metadata


def test_job_runner_preserves_ordered_event_sequence_numbers() -> None:
    """Event sequences should be strictly ordered in final JobResult payloads."""

    result = _run_success_job(
        clock_start=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
    )

    sequence_numbers = [event.sequence for event in result.events]
    assert sequence_numbers == [1, 2, 3, 4]
    assert [event.kind for event in result.events] == [
        JobEventKind.PROGRESS,
        JobEventKind.PROGRESS,
        JobEventKind.PROGRESS,
        JobEventKind.PROGRESS,
    ]


def test_job_runner_cancellation_is_part_of_contract_semantics() -> None:
    """Cancellation should produce a deterministic cancelled outcome and diagnostic event."""

    cancelled_context = _make_context(cancellation_requested=lambda: True)
    runner = JobRunner(
        clock=_TickingClock(datetime(2026, 5, 2, 8, 0, tzinfo=timezone.utc))
    )
    execute_called = False

    def _execute(_events) -> JobRunPayload:
        nonlocal execute_called
        execute_called = True
        return JobRunPayload(metadata={"exit_code": 0})

    result = runner.run(
        request=_make_request(),
        context=cancelled_context,
        execute=_execute,
    )

    assert execute_called is False
    assert result.outcome == JobOutcome.CANCELLED
    assert result.metadata["cancelled"] is True
    assert result.events[-1].kind == JobEventKind.DIAGNOSTIC
    assert result.events[-1].diagnostic is not None
    assert result.events[-1].diagnostic.code == "job_cancelled"


def test_job_result_rejects_non_monotonic_event_sequences() -> None:
    """Contract should reject JobResult payloads with out-of-order events."""

    event_two = JobEvent(
        sequence=2,
        occurred_at_utc=datetime(2026, 5, 1, tzinfo=timezone.utc),
        kind=JobEventKind.PROGRESS,
        progress=JobProgress(phase="start", message="start"),
    )
    event_one = JobEvent(
        sequence=1,
        occurred_at_utc=datetime(2026, 5, 1, 0, 0, 1, tzinfo=timezone.utc),
        kind=JobEventKind.DIAGNOSTIC,
        diagnostic=JobDiagnostic(
            severity=JobDiagnosticSeverity.INFO,
            message="info",
        ),
    )

    with pytest.raises(ValueError):
        JobResult(
            request=_make_request(),
            context=_make_context(),
            outcome=JobOutcome.SUCCEEDED,
            events=(event_two, event_one),
        )
