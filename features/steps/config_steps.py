"""Behave steps for unified profile hierarchy/discovery behavior."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from behave import given, then, when

from jbom.config.unified import load_unified


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


@given('sandbox unified profile "{profile_name}" contains:')
def given_sandbox_unified_profile_contains(context, profile_name: str) -> None:
    """Write a profile file to <sandbox>/.jbom/<profile>.jbom.yaml."""
    jbom_dir = Path(context.sandbox_root) / ".jbom"
    jbom_dir.mkdir(parents=True, exist_ok=True)
    profile_path = jbom_dir / f"{profile_name}.jbom.yaml"
    profile_path.write_text((context.text or "").strip() + "\n", encoding="utf-8")


@given(
    'profile directory "{directory_name}" has unified profile "{profile_name}" containing:'
)
def given_profile_directory_has_unified_profile(
    context, directory_name: str, profile_name: str
) -> None:
    """Write a profile file to <sandbox>/<directory_name>/<profile>.jbom.yaml."""
    target_dir = Path(context.sandbox_root) / directory_name
    target_dir.mkdir(parents=True, exist_ok=True)
    profile_path = target_dir / f"{profile_name}.jbom.yaml"
    profile_path.write_text((context.text or "").strip() + "\n", encoding="utf-8")


@given('JBOM_PROFILE_PATH contains "{directory_names_csv}"')
def given_jbom_profile_path_contains(context, directory_names_csv: str) -> None:
    """Set JBOM_PROFILE_PATH to the specified sandbox-relative directories."""
    dirs = [name.strip() for name in directory_names_csv.split(",") if name.strip()]
    abs_dirs = [str((Path(context.sandbox_root) / name).resolve()) for name in dirs]
    context.jbom_profile_path_override = os.pathsep.join(abs_dirs)


@when('I load unified profile "{profile_name}"')
def when_i_load_unified_profile(context, profile_name: str) -> None:
    """Load a unified profile with optional JBOM_PROFILE_PATH override."""
    previous = os.environ.get("JBOM_PROFILE_PATH")
    try:
        override = getattr(context, "jbom_profile_path_override", None)
        if override is None:
            os.environ.pop("JBOM_PROFILE_PATH", None)
        else:
            os.environ["JBOM_PROFILE_PATH"] = override
        context.loaded_unified_profile = load_unified(
            profile_name, cwd=Path(context.sandbox_root)
        )
    finally:
        if previous is None:
            os.environ.pop("JBOM_PROFILE_PATH", None)
        else:
            os.environ["JBOM_PROFILE_PATH"] = previous


@then('merged profile path "{dotted_path}" should equal "{expected_value}"')
def then_merged_profile_path_should_equal(
    context, dotted_path: str, expected_value: str
) -> None:
    """Assert a scalar merged-profile path equals expected string value."""
    loaded = getattr(context, "loaded_unified_profile", None)
    assert isinstance(loaded, dict), "No merged profile loaded"
    found, actual = _resolve_path(loaded, dotted_path)
    assert found, f"Merged profile path not found: {dotted_path}"
    assert str(actual) == expected_value, (
        f"Merged profile path mismatch for {dotted_path}: "
        f"expected {expected_value!r}, got {actual!r}"
    )


@then('merged profile path "{dotted_path}" should equal list "{expected_csv}"')
def then_merged_profile_path_should_equal_list(
    context, dotted_path: str, expected_csv: str
) -> None:
    """Assert a merged-profile path equals the expected comma-separated list."""
    loaded = getattr(context, "loaded_unified_profile", None)
    assert isinstance(loaded, dict), "No merged profile loaded"
    found, actual = _resolve_path(loaded, dotted_path)
    assert found, f"Merged profile path not found: {dotted_path}"
    assert isinstance(
        actual, list
    ), f"Merged profile path {dotted_path} expected list, got {type(actual).__name__}"
    expected = [item.strip() for item in expected_csv.split(",") if item.strip()]
    assert actual == expected, (
        f"Merged profile list mismatch for {dotted_path}: "
        f"expected {expected!r}, got {actual!r}"
    )


@then('merged profile path "{dotted_path}" should be missing')
def then_merged_profile_path_should_be_missing(context, dotted_path: str) -> None:
    """Assert a merged-profile path does not exist."""
    loaded = getattr(context, "loaded_unified_profile", None)
    assert isinstance(loaded, dict), "No merged profile loaded"
    found, _ = _resolve_path(loaded, dotted_path)
    assert not found, f"Expected merged profile path to be missing: {dotted_path}"
