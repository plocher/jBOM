"""Behave steps for profile hierarchy/discovery behavior."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from behave import given, then, when

from jbom.config.unified import load_unified

_DEFAULT_NAMED_PROFILE = "named"


def _resolve_path(root: Any, dotted_path: str) -> tuple[bool, Any]:
    """Resolve a dotted path into nested dict/list structures."""
    current: Any = root
    for token in str(dotted_path or "").split("."):
        key = token.strip()
        if not key:
            continue
        if isinstance(current, dict):
            if key not in current:
                return False, None
            current = current[key]
            continue
        if isinstance(current, list):
            try:
                index = int(key)
            except ValueError:
                return False, None
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
            continue
        return False, None
    return True, current


def _active_named_profile_name(context) -> str:
    """Return the active anonymous named-profile id for this scenario."""
    value = str(getattr(context, "active_named_profile_name", "") or "").strip().lower()
    return value or _DEFAULT_NAMED_PROFILE


def _profile_load_cwd(context) -> Path:
    """Return the cwd used for profile resolution."""
    value = getattr(context, "profile_load_cwd", None)
    if isinstance(value, Path):
        return value
    return Path(context.sandbox_root).resolve()


def _profile_repo_root(context) -> Path:
    """Return the simulated repo root used for profile resolution."""
    value = getattr(context, "profile_repo_root", None)
    if isinstance(value, Path):
        return value
    return _profile_load_cwd(context)


def _profile_home_root(context) -> Path:
    """Return the simulated HOME directory for profile resolution."""
    value = getattr(context, "profile_home_root", None)
    if isinstance(value, Path):
        return value
    return (Path(context.sandbox_root) / "_home").resolve()


def _profile_dir_for_tier(context, tier: str) -> Path:
    """Return the .jbom profile directory for a resolution tier."""
    normalized_tier = str(tier or "").strip().lower()
    if normalized_tier == "cwd":
        return _profile_load_cwd(context) / ".jbom"
    if normalized_tier == "repo":
        return _profile_repo_root(context) / ".jbom"
    if normalized_tier == "home":
        return _profile_home_root(context) / ".jbom"
    raise ValueError(f"Unknown profile tier: {tier!r}")


def _write_profile_file(context, profile_name: str, base_dir: Path) -> None:
    """Write a profile file to the specified directory."""
    base_dir.mkdir(parents=True, exist_ok=True)
    profile_path = base_dir / f"{profile_name}.jbom.yaml"
    profile_path.write_text((context.text or "").strip() + "\n", encoding="utf-8")


@given('a named profile "{profile_name}" that contains:')
def given_named_profile_contains(context, profile_name: str) -> None:
    """Write a profile file to <sandbox>/.jbom/<profile>.jbom.yaml."""
    context.active_named_profile_name = str(profile_name or "").strip().lower()
    _write_profile_file(context, profile_name, _profile_dir_for_tier(context, "cwd"))


@given("a named profile that contains:")
def given_anonymous_named_profile_contains(context) -> None:
    """Write an anonymous named profile to <sandbox>/.jbom/named.jbom.yaml."""
    given_named_profile_contains(context, _active_named_profile_name(context))


@given("a common profile that contains:")
def given_common_profile_contains(context) -> None:
    """Write common profile file in the active cwd tier."""
    _write_profile_file(context, "common", _profile_dir_for_tier(context, "cwd"))


@given('the profile load cwd is "{rel_path}"')
def given_profile_load_cwd_is(context, rel_path: str) -> None:
    """Set the cwd used by profile resolution to sandbox/<rel_path>."""
    load_cwd = (Path(context.sandbox_root) / rel_path).resolve()
    load_cwd.mkdir(parents=True, exist_ok=True)
    context.profile_load_cwd = load_cwd


@given('the profile repo root is "{rel_path}"')
def given_profile_repo_root_is(context, rel_path: str) -> None:
    """Set a simulated repo root and create .git marker for repo-root discovery."""
    repo_root = (Path(context.sandbox_root) / rel_path).resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    context.profile_repo_root = repo_root


@given("a cwd named profile that contains:")
def given_cwd_named_profile_contains(context) -> None:
    """Write anonymous named profile in the cwd tier."""
    _write_profile_file(
        context,
        _active_named_profile_name(context),
        _profile_dir_for_tier(context, "cwd"),
    )


@given("a cwd common profile that contains:")
def given_cwd_common_profile_contains(context) -> None:
    """Write common profile in the cwd tier."""
    _write_profile_file(context, "common", _profile_dir_for_tier(context, "cwd"))


@given("a repo named profile that contains:")
def given_repo_named_profile_contains(context) -> None:
    """Write anonymous named profile in the repo-root tier."""
    _write_profile_file(
        context,
        _active_named_profile_name(context),
        _profile_dir_for_tier(context, "repo"),
    )


@given("a repo common profile that contains:")
def given_repo_common_profile_contains(context) -> None:
    """Write common profile in the repo-root tier."""
    _write_profile_file(context, "common", _profile_dir_for_tier(context, "repo"))


@given("a home named profile that contains:")
def given_home_named_profile_contains(context) -> None:
    """Write anonymous named profile in the home tier."""
    _write_profile_file(
        context,
        _active_named_profile_name(context),
        _profile_dir_for_tier(context, "home"),
    )


@given("a home common profile that contains:")
def given_home_common_profile_contains(context) -> None:
    """Write common profile in the home tier."""
    _write_profile_file(context, "common", _profile_dir_for_tier(context, "home"))


@given('profile directory "{directory_name}" has profile "{profile_name}" containing:')
def given_profile_directory_has_profile(
    context, directory_name: str, profile_name: str
) -> None:
    """Write a profile file to <sandbox>/<directory_name>/<profile>.jbom.yaml."""
    target_dir = Path(context.sandbox_root) / directory_name
    _write_profile_file(context, profile_name, target_dir)


@given('profile directory "{directory_name}" has a named profile containing:')
def given_profile_directory_has_anonymous_named_profile(
    context, directory_name: str
) -> None:
    """Write anonymous named profile file under a specific profile directory."""
    given_profile_directory_has_profile(
        context, directory_name, _active_named_profile_name(context)
    )


@given('profile directory "{directory_name}" has a common profile containing:')
def given_profile_directory_has_common_profile(context, directory_name: str) -> None:
    """Write common profile file under a specific profile directory."""
    given_profile_directory_has_profile(context, directory_name, "common")


@given('JBOM_PROFILE_PATH contains "{directory_names_csv}"')
def given_jbom_profile_path_contains(context, directory_names_csv: str) -> None:
    """Set JBOM_PROFILE_PATH to the specified sandbox-relative directories."""
    dirs = [name.strip() for name in directory_names_csv.split(",") if name.strip()]
    abs_dirs = [str((Path(context.sandbox_root) / name).resolve()) for name in dirs]
    context.jbom_profile_path_override = os.pathsep.join(abs_dirs)


@when('I load profile "{profile_name}"')
def when_i_load_profile(context, profile_name: str) -> None:
    """Load a profile with optional JBOM_PROFILE_PATH override."""
    previous = os.environ.get("JBOM_PROFILE_PATH")
    previous_home = os.environ.get("HOME")
    try:
        override = getattr(context, "jbom_profile_path_override", None)
        if override is None:
            os.environ.pop("JBOM_PROFILE_PATH", None)
        else:
            os.environ["JBOM_PROFILE_PATH"] = override
        simulated_home = _profile_home_root(context)
        simulated_home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(simulated_home)
        context.loaded_profile = load_unified(
            profile_name, cwd=_profile_load_cwd(context)
        )
    finally:
        if previous is None:
            os.environ.pop("JBOM_PROFILE_PATH", None)
        else:
            os.environ["JBOM_PROFILE_PATH"] = previous
        if previous_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = previous_home


@when("I load the named profile")
def when_i_load_the_named_profile(context) -> None:
    """Load the active anonymous named profile."""
    when_i_load_profile(context, _active_named_profile_name(context))


@then('resolved profile value "{dotted_path}" should equal "{expected_value}"')
def then_resolved_profile_value_should_equal(
    context, dotted_path: str, expected_value: str
) -> None:
    """Assert a scalar resolved-profile value equals expected string value."""
    loaded = getattr(context, "loaded_profile", None)
    assert isinstance(loaded, dict), "No resolved profile loaded"
    found, actual = _resolve_path(loaded, dotted_path)
    assert found, f"Resolved profile value not found: {dotted_path}"
    assert str(actual) == expected_value, (
        f"Resolved profile value mismatch for {dotted_path}: "
        f"expected {expected_value!r}, got {actual!r}"
    )


@then('resolved profile value "{dotted_path}" should equal list "{expected_csv}"')
def then_resolved_profile_value_should_equal_list(
    context, dotted_path: str, expected_csv: str
) -> None:
    """Assert a resolved-profile value equals the expected comma-separated list."""
    loaded = getattr(context, "loaded_profile", None)
    assert isinstance(loaded, dict), "No resolved profile loaded"
    found, actual = _resolve_path(loaded, dotted_path)
    assert found, f"Resolved profile value not found: {dotted_path}"
    assert isinstance(
        actual, list
    ), f"Resolved profile value {dotted_path} expected list, got {type(actual).__name__}"
    expected = [item.strip() for item in expected_csv.split(",") if item.strip()]
    assert actual == expected, (
        f"Resolved profile list mismatch for {dotted_path}: "
        f"expected {expected!r}, got {actual!r}"
    )


@then('resolved profile value "{dotted_path}" should be missing')
def then_resolved_profile_value_should_be_missing(context, dotted_path: str) -> None:
    """Assert a resolved-profile value does not exist."""
    loaded = getattr(context, "loaded_profile", None)
    assert isinstance(loaded, dict), "No resolved profile loaded"
    found, _ = _resolve_path(loaded, dotted_path)
    assert not found, f"Expected resolved profile value to be missing: {dotted_path}"
