"""Unit tests for scripts/post_merge_cleanup.py subprocess hardening (#364).

Covers the anti-hang guarantees of ``run_git``:
- stdin is redirected to DEVNULL so git can never block on hidden prompts
- interactive prompting is disabled via GIT_TERMINAL_PROMPT / ssh BatchMode
- network operations (fetch/prune, remote delete) pass a timeout
- a timeout expiry is converted into a failed result, not an exception
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "post_merge_cleanup.py"


@pytest.fixture(scope="module")
def cleanup_module() -> ModuleType:
    """Load scripts/post_merge_cleanup.py as an importable module."""
    spec = importlib.util.spec_from_file_location("post_merge_cleanup", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def _completed(returncode: int = 0) -> subprocess.CompletedProcess[str]:
    """Build a benign CompletedProcess for mocking subprocess.run."""
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout="", stderr=""
    )


class TestRunGitHardening:
    """run_git must be immune to interactive prompts and silent stalls."""

    def test_stdin_redirected_to_devnull(self, cleanup_module: ModuleType) -> None:
        """git subprocesses must not inherit the TTY on stdin."""
        with mock.patch("subprocess.run", return_value=_completed()) as run_mock:
            cleanup_module.run_git(["status"])
        assert run_mock.call_args.kwargs["stdin"] == subprocess.DEVNULL

    def test_terminal_prompts_disabled(self, cleanup_module: ModuleType) -> None:
        """Child env must set GIT_TERMINAL_PROMPT=0 and ssh BatchMode."""
        with mock.patch("subprocess.run", return_value=_completed()) as run_mock:
            cleanup_module.run_git(["status"])
        env = run_mock.call_args.kwargs["env"]
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert "BatchMode=yes" in env["GIT_SSH_COMMAND"]

    def test_existing_git_ssh_command_respected(
        self, cleanup_module: ModuleType
    ) -> None:
        """A caller-provided GIT_SSH_COMMAND must not be overridden."""
        with mock.patch.dict(os.environ, {"GIT_SSH_COMMAND": "custom-ssh -i key"}):
            with mock.patch("subprocess.run", return_value=_completed()) as run_mock:
                cleanup_module.run_git(["status"])
        env = run_mock.call_args.kwargs["env"]
        assert env["GIT_SSH_COMMAND"] == "custom-ssh -i key"

    def test_timeout_forwarded_to_subprocess(self, cleanup_module: ModuleType) -> None:
        """An explicit timeout must reach subprocess.run."""
        with mock.patch("subprocess.run", return_value=_completed()) as run_mock:
            cleanup_module.run_git(["push"], timeout=42.0)
        assert run_mock.call_args.kwargs["timeout"] == 42.0

    def test_timeout_expiry_becomes_failed_result(
        self, cleanup_module: ModuleType
    ) -> None:
        """TimeoutExpired must surface as a failed result with a clear error."""
        with mock.patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git", "push"], timeout=5.0),
        ):
            result = cleanup_module.run_git(["push"], timeout=5.0)
        assert result.returncode != 0
        assert "timed out" in result.stderr


class TestNetworkOperationTimeouts:
    """Network-facing helpers must bound their git calls with a timeout."""

    def test_fetch_and_prune_uses_network_timeout(
        self, cleanup_module: ModuleType
    ) -> None:
        """fetch --prune must pass the module network timeout."""
        with mock.patch.object(
            cleanup_module, "run_git", return_value=_completed()
        ) as run_git_mock:
            code = cleanup_module.fetch_and_prune(
                "origin", dry_run=False, verbose=False
            )
        assert code == 0
        assert (
            run_git_mock.call_args.kwargs["timeout"]
            == cleanup_module.GIT_NETWORK_TIMEOUT_SECONDS
        )

    def test_delete_remote_branch_uses_network_timeout(
        self, cleanup_module: ModuleType
    ) -> None:
        """push --delete must pass the module network timeout."""
        with mock.patch.object(
            cleanup_module, "run_git", return_value=_completed()
        ) as run_git_mock:
            code = cleanup_module.delete_remote_branch(
                "origin", "feature/x", dry_run=False, verbose=False
            )
        assert code == 0
        assert (
            run_git_mock.call_args.kwargs["timeout"]
            == cleanup_module.GIT_NETWORK_TIMEOUT_SECONDS
        )

    def test_timed_out_remote_delete_reports_error(
        self, cleanup_module: ModuleType
    ) -> None:
        """A timed-out remote delete must return a non-zero code, not hang."""
        timed_out = subprocess.CompletedProcess(
            args=["git"], returncode=124, stdout="", stderr="timed out after 5.0s"
        )
        with mock.patch.object(cleanup_module, "run_git", return_value=timed_out):
            code = cleanup_module.delete_remote_branch(
                "origin", "feature/x", dry_run=False, verbose=False
            )
        assert code != 0
