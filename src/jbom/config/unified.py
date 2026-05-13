"""Unified ``*.jbom.yaml`` profile loading and stanza extraction.

Implements ADR 0008 Phase 1b core behavior:
- named profile lookup: first-match-wins
- ``common.jbom.yaml`` chain: cumulative merge
- ``extends:`` chain with circular detection
- deep merge semantics: dict-merge, list-replace, null-delete
- ``policy.jbom.yaml`` detection with NOTICE-level logging (enforcement deferred)
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, MutableMapping

import yaml

from jbom.config import profile_search as _profile_search

# ``profile_search_dirs`` is re-exported here so legacy callers and tests can
# monkeypatch ``jbom.config.unified.profile_search_dirs``; ``_effective_search_dirs``
# resolves it via the module at call time so the patch takes effect.
from jbom.config.profile_search import profile_search_dirs  # noqa: F401

if TYPE_CHECKING:
    from jbom.config.defaults import DefaultsConfig
    from jbom.config.fabricators import FabricatorConfig
    from jbom.config.suppliers import SupplierConfig

log = logging.getLogger(__name__)

_BUILTIN_DIR = Path(__file__).parent / "profiles"
_PROFILE_SUFFIX = ".jbom.yaml"
_COMMON_PROFILE_NAME = "common"
_POLICY_PROFILE_NAME = "policy"
_VALID_STANZA_NAMES = frozenset({"fab", "supplier", "defaults", "presets"})


def _emit_profile_eval(message: str) -> None:
    """Best-effort profile evaluation trace emission."""
    try:
        recorder = getattr(_profile_search, "record_profile_eval", None)
        if callable(recorder):
            recorder(message)
            return
    except Exception:
        pass
    try:
        print(message, flush=True)
    except Exception:
        pass


class UnifiedProfileNotFoundError(ValueError):
    """Raised when a named ``*.jbom.yaml`` profile cannot be found."""


def load_unified(
    name: str,
    *,
    cwd: Path | None = None,
    builtin_dir: Path | None = None,
) -> dict[str, Any]:
    """Load and merge a named ``*.jbom.yaml`` profile.

    Resolution order:
    1) cumulative common chain (`common.jbom.yaml`) across all search dirs
    2) named profile first-match across the same search dirs
    3) named profile ``extends:`` chain (parent merged first)

    Args:
        name: Named profile ID (e.g. ``"jlc"``).
        cwd: Optional cwd override for search path resolution.
        builtin_dir: Optional final fallback directory for built-in profiles.

    Returns:
        Fully merged unified profile mapping.

    Raises:
        UnifiedProfileNotFoundError: profile cannot be found.
        ValueError: invalid YAML shape or circular extends.
    """

    normalized_name = _normalize_profile_name(name)
    if not normalized_name:
        raise ValueError("Unified profile name must be a non-empty string")

    search_dirs = _effective_search_dirs(cwd=cwd, builtin_dir=builtin_dir)
    _log_policy_profile_notice(search_dirs)

    common_chain = _load_common_chain(search_dirs)
    named_profile = _load_named_profile_chain(
        normalized_name, search_dirs, visiting_stack=[]
    )
    return _deep_merge(common_chain, named_profile)


def list_unified_stanza_ids(
    stanza_name: str,
    *,
    cwd: Path | None = None,
    builtin_dir: Path | None = None,
) -> list[str]:
    """List effective stanza IDs from discoverable unified profiles.

    Named profiles are discovered with first-match-wins by filename. For each
    selected profile, the effective ID for the requested stanza is:
    - ``<stanza>.id`` when present
    - otherwise top-level ``id``
    - otherwise profile filename stem
    """

    normalized_stanza = str(stanza_name or "").strip().lower()
    if normalized_stanza not in _VALID_STANZA_NAMES:
        raise ValueError(
            f"Unknown unified stanza name {stanza_name!r}; expected one of "
            f"{sorted(_VALID_STANZA_NAMES)}"
        )

    search_dirs = _effective_search_dirs(cwd=cwd, builtin_dir=builtin_dir)
    _emit_profile_eval(
        "[jBOM] unified eval "
        f"stanza={normalized_stanza!r} search_dirs={[str(path) for path in search_dirs]}"
    )
    profile_names = _discover_named_profile_names(search_dirs)
    _emit_profile_eval(
        "[jBOM] unified eval "
        f"stanza={normalized_stanza!r} discovered_profiles={profile_names}"
    )

    discovered_ids: set[str] = set()
    for profile_name in profile_names:
        try:
            merged_named = _load_named_profile_chain(
                profile_name, search_dirs, visiting_stack=[]
            )
        except (UnifiedProfileNotFoundError, ValueError) as exc:
            _emit_profile_eval(
                "[jBOM] unified skip "
                f"stanza={normalized_stanza!r} profile={profile_name!r} reason={exc}"
            )
            continue

        raw_stanza = merged_named.get(normalized_stanza)
        if not isinstance(raw_stanza, dict):
            _emit_profile_eval(
                "[jBOM] unified skip "
                f"stanza={normalized_stanza!r} profile={profile_name!r} reason=no_stanza"
            )
            continue
        stanza_mapping = dict(raw_stanza)
        effective_id = _effective_stanza_id(
            merged_named, stanza_mapping, fallback=profile_name
        )
        if effective_id:
            discovered_ids.add(effective_id)
            _emit_profile_eval(
                "[jBOM] unified match "
                f"stanza={normalized_stanza!r} profile={profile_name!r} id={effective_id!r}"
            )

    sorted_ids = sorted(discovered_ids)
    _emit_profile_eval(
        "[jBOM] unified result " f"stanza={normalized_stanza!r} ids={sorted_ids}"
    )
    return sorted_ids


def resolve_profile_name_for_stanza_id(
    stanza_name: str,
    stanza_id: str,
    *,
    cwd: Path | None = None,
    builtin_dir: Path | None = None,
) -> str | None:
    """Resolve which named profile owns a stanza with effective ID ``stanza_id``."""

    normalized_stanza = str(stanza_name or "").strip().lower()
    if normalized_stanza not in _VALID_STANZA_NAMES:
        raise ValueError(
            f"Unknown unified stanza name {stanza_name!r}; expected one of "
            f"{sorted(_VALID_STANZA_NAMES)}"
        )

    normalized_id = _normalize_profile_name(stanza_id)
    if not normalized_id:
        return None

    search_dirs = _effective_search_dirs(cwd=cwd, builtin_dir=builtin_dir)
    profile_names = _discover_named_profile_names(search_dirs)
    for profile_name in profile_names:
        try:
            merged_named = _load_named_profile_chain(
                profile_name, search_dirs, visiting_stack=[]
            )
        except (UnifiedProfileNotFoundError, ValueError):
            continue

        raw_stanza = merged_named.get(normalized_stanza)
        if not isinstance(raw_stanza, dict):
            continue
        effective_id = _effective_stanza_id(
            merged_named, dict(raw_stanza), fallback=profile_name
        )
        if effective_id == normalized_id:
            return profile_name
    return None


def fab_stanza(merged: Mapping[str, Any], *, default_id: str) -> "FabricatorConfig":
    """Extract and validate the ``fab:`` stanza as ``FabricatorConfig``."""

    from jbom.config.fabricators import FabricatorConfig

    stanza = _require_stanza_mapping(merged, "fab")
    effective_id = _effective_stanza_id(merged, stanza, fallback=default_id)
    return FabricatorConfig.model_validate(stanza, context={"default_id": effective_id})


def supplier_stanza(merged: Mapping[str, Any], *, default_id: str) -> "SupplierConfig":
    """Extract and validate the ``supplier:`` stanza as ``SupplierConfig``."""

    from jbom.config.suppliers import SupplierConfig

    stanza = _require_stanza_mapping(merged, "supplier")
    effective_id = _effective_stanza_id(merged, stanza, fallback=default_id)
    return SupplierConfig.model_validate(stanza, context={"default_id": effective_id})


def defaults_stanza(merged: Mapping[str, Any], *, default_id: str) -> "DefaultsConfig":
    """Extract and validate the ``defaults:`` stanza as ``DefaultsConfig``."""

    from jbom.config.defaults import DefaultsConfig

    stanza = _require_stanza_mapping(merged, "defaults")
    effective_id = _effective_stanza_id(merged, stanza, fallback=default_id)
    return DefaultsConfig.model_validate(stanza, context={"profile_name": effective_id})


def _effective_search_dirs(*, cwd: Path | None, builtin_dir: Path | None) -> list[Path]:
    # Look up profile_search_dirs from this module so tests can monkeypatch
    # `jbom.config.unified.profile_search_dirs` (legacy import surface).
    import jbom.config.unified as _self

    dirs = list(_self.profile_search_dirs(cwd=cwd))
    dirs.append((builtin_dir or _BUILTIN_DIR).resolve())
    return _dedupe_paths(dirs)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _load_common_chain(search_dirs: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for directory in reversed(search_dirs):
        common_path = directory / f"{_COMMON_PROFILE_NAME}{_PROFILE_SUFFIX}"
        if not common_path.is_file():
            continue
        common_data = _load_yaml_mapping(common_path, context="common profile")
        merged = _deep_merge(merged, common_data)
    return merged


def _load_named_profile_chain(
    name: str,
    search_dirs: list[Path],
    *,
    visiting_stack: list[str],
) -> dict[str, Any]:
    normalized_name = _normalize_profile_name(name)
    if not normalized_name:
        raise ValueError("extends target must be a non-empty profile name")

    if normalized_name in visiting_stack:
        cycle = " -> ".join([*visiting_stack, normalized_name])
        raise ValueError(f"Circular extends chain detected: {cycle}")

    profile_path = _find_named_profile_path(normalized_name, search_dirs)
    if profile_path is None:
        raise UnifiedProfileNotFoundError(
            f"Unified profile not found: {normalized_name!r}. "
            f"Place {normalized_name}{_PROFILE_SUFFIX} in a .jbom/ directory "
            f"or in $JBOM_PROFILE_PATH."
        )

    raw = _load_yaml_mapping(profile_path, context=f"profile {normalized_name!r}")
    extends_raw = raw.get("extends")
    child_data = dict(raw)
    child_data.pop("extends", None)

    if extends_raw is None:
        return child_data
    if not isinstance(extends_raw, str) or not extends_raw.strip():
        raise ValueError(
            f"Profile {normalized_name!r} has invalid extends value; "
            "expected a non-empty string"
        )

    parent_name = extends_raw.strip()
    parent_data = _load_named_profile_chain(
        parent_name,
        search_dirs,
        visiting_stack=[*visiting_stack, normalized_name],
    )
    return _deep_merge(parent_data, child_data)


def _find_named_profile_path(name: str, search_dirs: list[Path]) -> Path | None:
    filename = f"{name}{_PROFILE_SUFFIX}"
    for directory in search_dirs:
        candidate = directory / filename
        if candidate.is_file():
            return candidate
    return None


def _discover_named_profile_names(search_dirs: list[Path]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(f"*{_PROFILE_SUFFIX}")):
            profile_name = path.name[: -len(_PROFILE_SUFFIX)]
            normalized_name = _normalize_profile_name(profile_name)
            if not normalized_name:
                continue
            if normalized_name in {_COMMON_PROFILE_NAME, _POLICY_PROFILE_NAME}:
                continue
            if normalized_name in seen:
                continue
            seen.add(normalized_name)
            names.append(normalized_name)
    return names


def _effective_stanza_id(
    merged: Mapping[str, Any], stanza: Mapping[str, Any], *, fallback: str
) -> str:
    stanza_id = stanza.get("id")
    if isinstance(stanza_id, str) and stanza_id.strip():
        return _normalize_profile_name(stanza_id)

    merged_id = merged.get("id")
    if isinstance(merged_id, str) and merged_id.strip():
        return _normalize_profile_name(merged_id)

    return _normalize_profile_name(fallback)


def _require_stanza_mapping(
    merged: Mapping[str, Any], stanza_name: str
) -> dict[str, Any]:
    stanza_value = merged.get(stanza_name)
    if stanza_value is None:
        raise ValueError(
            f"Unified profile does not define required '{stanza_name}:' stanza"
        )
    if not isinstance(stanza_value, dict):
        raise ValueError(f"Unified profile '{stanza_name}:' stanza must be a mapping")
    return dict(stanza_value)


def _load_yaml_mapping(path: Path, *, context: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle) or {}
    if not isinstance(parsed, MutableMapping):
        raise ValueError(f"{context} at {path} must be a YAML mapping")
    return dict(parsed)


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Deep-merge override onto base.

    Semantics:
    - dictionaries merge recursively
    - lists replace
    - scalars replace
    - ``null`` deletes inherited keys
    """

    result: dict[str, Any] = copy.deepcopy(dict(base))
    for key, override_value in override.items():
        if override_value is None:
            result.pop(key, None)
            continue

        existing = result.get(key)
        if isinstance(existing, dict) and isinstance(override_value, dict):
            result[key] = _deep_merge(existing, override_value)
            continue

        result[key] = copy.deepcopy(override_value)

    return result


def _normalize_profile_name(name: str) -> str:
    return str(name or "").strip().lower()


def _log_policy_profile_notice(search_dirs: list[Path]) -> None:
    for directory in search_dirs:
        policy_path = directory / f"{_POLICY_PROFILE_NAME}{_PROFILE_SUFFIX}"
        if policy_path.is_file():
            log.info(
                "NOTICE: policy.jbom.yaml detected at %s; policy enforcement is deferred",
                policy_path,
            )


__all__ = [
    "UnifiedProfileNotFoundError",
    "defaults_stanza",
    "fab_stanza",
    "list_unified_stanza_ids",
    "load_unified",
    "resolve_profile_name_for_stanza_id",
    "supplier_stanza",
]
