#!/usr/bin/env python3
"""Safely clean merged feature branches using patch-equivalence checks.

This script enforces the repository's post-merge cleanup policy:
1) refresh refs (`git fetch --prune <remote>`)
2) verify branch patch-equivalence against `<remote>/<base>` using `git cherry -v`
3) delete local + remote branch only when the branch is patch-equivalent

Output style:
- default mode is quiet on the normative/success path
- warnings/errors surface abnormal states (unmerged content, skipped current branch, etc.)
- `--verbose` enables detailed per-branch diagnostics

RFE behavior:
- if `--branch` is omitted, the script iterates eligible non-base branches
  discovered from local + remote refs.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass

#: Upper bound for git operations that touch the network (fetch, push).
#: Generous enough for slow links; prevents indefinite silent stalls.
GIT_NETWORK_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class BranchState:
    """Local/remote state for a branch targeted for cleanup."""

    branch: str
    remote: str
    local_exists: bool
    remote_exists: bool
    current_branch: str | None


@dataclass(frozen=True)
class CherryResult:
    """Structured result from `git cherry -v <base> <branch_ref>`."""

    base_ref: str
    branch_ref: str
    raw_lines: tuple[str, ...]
    equivalent_lines: tuple[str, ...]
    unique_lines: tuple[str, ...]

    @property
    def is_safe_to_delete(self) -> bool:
        """Return True when no unique (`+`) commits exist."""
        return not self.unique_lines


@dataclass(frozen=True)
class CleanupOutcome:
    """Result of one branch cleanup attempt."""

    branch: str
    status: str
    message: str
    unique_lines: tuple[str, ...] = ()
    equivalent_lines: tuple[str, ...] = ()
    error_detail: str | None = None

    @property
    def is_warning(self) -> bool:
        """Return True when outcome represents abnormal but non-fatal state."""
        return self.status in {"unmerged", "skipped_current", "skipped_base"}

    @property
    def is_error(self) -> bool:
        """Return True when outcome is a hard failure."""
        return self.status in {"error", "not_found"}


def run_git(
    args: list[str], *, capture_output: bool = True, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the completed process without raising.

    Hardened against silent hangs (#364):
    - stdin is redirected to DEVNULL so git can never block on hidden prompts
      (prompt text would otherwise be swallowed by the captured stderr)
    - GIT_TERMINAL_PROMPT=0 and ssh BatchMode make git fail fast instead of
      prompting for credentials/passphrases/host keys
    - an optional timeout bounds network operations; expiry is converted to
      a failed CompletedProcess rather than an exception
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")
    cmd = ["git", "--no-pager", *args]
    try:
        return subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=capture_output,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=124,
            stdout="",
            stderr=f"git {' '.join(args)} timed out after {timeout}s",
        )


def git_ref_exists(ref: str) -> bool:
    """Return True when a git ref exists."""
    result = run_git(["show-ref", "--verify", "--quiet", ref], capture_output=True)
    return result.returncode == 0


def get_current_branch() -> str | None:
    """Return current branch name, or None when detached/unknown."""
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"], capture_output=True)
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return None if value == "HEAD" else value


def fetch_and_prune(remote: str, *, dry_run: bool, verbose: bool) -> int:
    """Fetch and prune refs for the configured remote."""
    cmd = ["fetch", "--prune", remote]
    if dry_run:
        if verbose:
            print(f"[dry-run] git --no-pager {' '.join(cmd)}")
        return 0

    result = run_git(cmd, capture_output=True, timeout=GIT_NETWORK_TIMEOUT_SECONDS)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(f"Error: failed to fetch/prune {remote}: {stderr}", file=sys.stderr)
        return 2
    return 0


def resolve_branch_state(branch: str, remote: str) -> BranchState:
    """Collect local/remote existence and current checkout details."""
    local_ref = f"refs/heads/{branch}"
    remote_ref = f"refs/remotes/{remote}/{branch}"
    return BranchState(
        branch=branch,
        remote=remote,
        local_exists=git_ref_exists(local_ref),
        remote_exists=git_ref_exists(remote_ref),
        current_branch=get_current_branch(),
    )


def list_local_branches() -> tuple[str, ...]:
    """Return local branch names."""
    result = run_git(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads"], capture_output=True
    )
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def list_remote_branches(remote: str) -> tuple[str, ...]:
    """Return remote branch names (without `<remote>/` prefix)."""
    result = run_git(
        ["for-each-ref", "--format=%(refname:short)", f"refs/remotes/{remote}"],
        capture_output=True,
    )
    if result.returncode != 0:
        return ()

    values: list[str] = []
    prefix = f"{remote}/"
    for line in result.stdout.splitlines():
        token = line.strip()
        if not token or token == f"{remote}/HEAD":
            continue
        if token.startswith(prefix):
            values.append(token[len(prefix) :])
    return tuple(values)


def discover_candidate_branches(base: str, remote: str) -> tuple[str, ...]:
    """Return sorted candidate branches excluding base and current branch."""
    current = get_current_branch()
    names = set(list_local_branches()) | set(list_remote_branches(remote))
    excluded = {base}
    if current:
        excluded.add(current)
    return tuple(sorted(name for name in names if name and name not in excluded))


def run_cherry(base_ref: str, branch_ref: str) -> CherryResult:
    """Run patch-equivalence check and return structured commit classes."""
    result = run_git(["cherry", "-v", base_ref, branch_ref], capture_output=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"git cherry failed for {base_ref}...{branch_ref}: {stderr or 'unknown error'}"
        )

    lines = tuple(line.strip() for line in result.stdout.splitlines() if line.strip())
    equivalent_lines = tuple(line for line in lines if line.startswith("- "))
    unique_lines = tuple(line for line in lines if line.startswith("+ "))

    return CherryResult(
        base_ref=base_ref,
        branch_ref=branch_ref,
        raw_lines=lines,
        equivalent_lines=equivalent_lines,
        unique_lines=unique_lines,
    )


def delete_local_branch(branch: str, *, dry_run: bool, verbose: bool) -> int:
    """Delete a local branch with safe `-d` semantics."""
    cmd = ["branch", "-d", branch]
    if dry_run:
        if verbose:
            print(f"[dry-run] git --no-pager {' '.join(cmd)}")
        return 0

    result = run_git(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(
            f"Error: failed to delete local branch {branch}: {stderr}", file=sys.stderr
        )
        return 2
    return 0


def delete_remote_branch(
    remote: str, branch: str, *, dry_run: bool, verbose: bool
) -> int:
    """Delete a remote branch when it exists."""
    cmd = ["push", remote, "--delete", branch]
    if dry_run:
        if verbose:
            print(f"[dry-run] git --no-pager {' '.join(cmd)}")
        return 0

    result = run_git(cmd, capture_output=True, timeout=GIT_NETWORK_TIMEOUT_SECONDS)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(
            f"Error: failed to delete remote branch {remote}/{branch}: {stderr}",
            file=sys.stderr,
        )
        return 2
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description=(
            "Post-merge branch cleanup with patch-equivalence safety checks. "
            "Deletes local/remote branch only when git cherry shows no unique commits."
        )
    )
    parser.add_argument(
        "--branch",
        help=(
            "Feature branch name to clean up (without remote prefix). "
            "If omitted, all eligible non-base branches are evaluated."
        ),
    )
    parser.add_argument(
        "--base",
        default="main",
        help="Base branch to verify against (default: main)",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Remote name for fetch/delete operations (default: origin)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show checks and delete commands without changing refs",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed diagnostics, including patch-equivalence details",
    )
    return parser.parse_args(argv)


def cleanup_single_branch(args: argparse.Namespace, branch: str) -> CleanupOutcome:
    """Run cleanup policy for one branch and return structured outcome."""
    if branch == args.base:
        return CleanupOutcome(
            branch=branch,
            status="skipped_base",
            message=f"Warning: skipped base branch: {branch}",
        )
    state = resolve_branch_state(branch, args.remote)
    if not state.local_exists and not state.remote_exists:
        return CleanupOutcome(
            branch=branch,
            status="not_found",
            message=f"Error: branch not found: {branch}",
        )

    if state.current_branch == branch and not args.dry_run:
        return CleanupOutcome(
            branch=branch,
            status="skipped_current",
            message=f"Warning: skipped current branch: {branch}",
        )

    branch_ref = branch if state.local_exists else f"{args.remote}/{branch}"
    base_ref = f"{args.remote}/{args.base}"

    try:
        cherry_result = run_cherry(base_ref, branch_ref)
    except RuntimeError as exc:
        return CleanupOutcome(
            branch=branch,
            status="error",
            message=f"Error: patch-equivalence failed: {branch}",
            error_detail=str(exc),
        )

    if not cherry_result.is_safe_to_delete:
        return CleanupOutcome(
            branch=branch,
            status="unmerged",
            message=f"Warning: unmerged content: {branch}",
            unique_lines=cherry_result.unique_lines,
            equivalent_lines=cherry_result.equivalent_lines,
        )

    if state.local_exists:
        local_code = delete_local_branch(
            branch, dry_run=args.dry_run, verbose=args.verbose
        )
        if local_code != 0:
            return CleanupOutcome(
                branch=branch,
                status="error",
                message=f"Error: local delete failed: {branch}",
            )

    if state.remote_exists:
        remote_code = delete_remote_branch(
            args.remote, branch, dry_run=args.dry_run, verbose=args.verbose
        )
        if remote_code != 0:
            return CleanupOutcome(
                branch=branch,
                status="error",
                message=f"Error: remote delete failed: {branch}",
            )

    if args.dry_run:
        return CleanupOutcome(
            branch=branch,
            status="dry_run_success",
            message=f"Success: would delete: {branch}",
            equivalent_lines=cherry_result.equivalent_lines,
        )

    return CleanupOutcome(
        branch=branch,
        status="success",
        message=f"Success: deleted: {branch}",
        equivalent_lines=cherry_result.equivalent_lines,
    )


def emit_outcome(outcome: CleanupOutcome, *, verbose: bool) -> None:
    """Print one cleanup result using quiet-by-default policy."""
    print(outcome.message)

    if outcome.status == "unmerged":
        for line in outcome.unique_lines:
            print(f"  {line}")
        if verbose and outcome.equivalent_lines:
            print("  (equivalent commits)")
            for line in outcome.equivalent_lines:
                print(f"  {line}")
        return

    if verbose:
        if outcome.equivalent_lines:
            for line in outcome.equivalent_lines:
                print(f"  {line}")
        if outcome.error_detail:
            print(f"  {outcome.error_detail}")


def main(argv: list[str] | None = None) -> int:
    """Entry point for post-merge cleanup enforcement."""
    args = parse_args(argv)

    fetch_code = fetch_and_prune(
        args.remote, dry_run=args.dry_run, verbose=args.verbose
    )
    if fetch_code != 0:
        return fetch_code

    branches = (
        (args.branch,)
        if args.branch
        else discover_candidate_branches(base=args.base, remote=args.remote)
    )
    if not branches:
        print("Success: no branches eligible for cleanup")
        return 0

    warnings = 0
    errors = 0
    for branch in branches:
        outcome = cleanup_single_branch(args, branch)
        emit_outcome(outcome, verbose=args.verbose)
        if outcome.is_warning:
            warnings += 1
        if outcome.is_error:
            errors += 1

    if errors:
        return 2
    if warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
