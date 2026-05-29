"""Shared CLI helpers for supplier-related argument parsing."""

from __future__ import annotations

from typing import Any


def normalize_supplier_ids(raw_suppliers: Any) -> list[str]:
    """Normalize and de-duplicate supplier IDs while preserving input order."""

    if raw_suppliers is None:
        return []

    if isinstance(raw_suppliers, str):
        candidates = [raw_suppliers]
    elif isinstance(raw_suppliers, list):
        candidates = [str(value) for value in raw_suppliers]
    else:
        candidates = [str(raw_suppliers)]

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        supplier_id = candidate.strip().lower()
        if not supplier_id or supplier_id in seen:
            continue
        seen.add(supplier_id)
        normalized.append(supplier_id)

    return normalized


def parse_supplier_api_key_args(
    raw_api_keys: Any,
    *,
    supplier_ids: list[str],
) -> tuple[dict[str, str], str | None]:
    """Parse ``--api-key`` values into supplier-scoped and default keys.

    Supported forms:
    - ``--api-key KEY`` (single default key, backward compatible)
    - ``--api-key SUPPLIER_ID=KEY`` (supplier-scoped key; repeatable)
    - repeated ``--api-key KEY`` values when count matches ``--supplier`` count
      (mapped by argument order)

    Args:
        raw_api_keys: Parsed CLI value (None, string, or list of strings).
        supplier_ids: Supplier IDs selected via ``--supplier`` for validation.

    Returns:
        ``(scoped_keys, default_key)`` where ``scoped_keys`` maps supplier ID to key.

    Raises:
        ValueError: Invalid key syntax, duplicate entries, or supplier mismatch.
    """

    if raw_api_keys is None:
        return {}, None

    if isinstance(raw_api_keys, str):
        candidates = [raw_api_keys]
    elif isinstance(raw_api_keys, list):
        candidates = [str(value) for value in raw_api_keys]
    else:
        candidates = [str(raw_api_keys)]

    scoped_keys: dict[str, str] = {}
    unscoped_keys: list[str] = []
    normalized_supplier_ids: list[str] = []
    normalized_supplier_id_set: set[str] = set()
    for supplier_id in supplier_ids:
        normalized_supplier_id = str(supplier_id).strip().lower()
        if (
            not normalized_supplier_id
            or normalized_supplier_id in normalized_supplier_id_set
        ):
            continue
        normalized_supplier_id_set.add(normalized_supplier_id)
        normalized_supplier_ids.append(normalized_supplier_id)

    for candidate in candidates:
        token = str(candidate).strip()
        if not token:
            continue
        if "=" in token:
            supplier_token, key_value = token.split("=", 1)
            supplier_id = supplier_token.strip().lower()
            api_key = key_value.strip()
            if not supplier_id or not api_key:
                raise ValueError(
                    f"Invalid --api-key value {token!r}; use KEY or SUPPLIER_ID=KEY"
                )
            if (
                normalized_supplier_id_set
                and supplier_id not in normalized_supplier_id_set
            ):
                raise ValueError(
                    f"--api-key supplier '{supplier_id}' is not present in --supplier arguments"
                )
            if supplier_id in scoped_keys:
                raise ValueError(
                    f"Duplicate --api-key entry provided for supplier '{supplier_id}'"
                )
            scoped_keys[supplier_id] = api_key
            continue

        unscoped_keys.append(token)

    if scoped_keys and unscoped_keys:
        raise ValueError(
            "Cannot mix scoped and unscoped --api-key values; use either "
            "KEY values only or SUPPLIER_ID=KEY values only"
        )

    if scoped_keys:
        return scoped_keys, None

    if not unscoped_keys:
        return {}, None

    if len(unscoped_keys) == 1:
        return {}, unscoped_keys[0]

    if not normalized_supplier_ids:
        raise ValueError(
            "Multiple unscoped --api-key values require --supplier arguments "
            "or explicit SUPPLIER_ID=KEY mapping"
        )

    if len(unscoped_keys) != len(normalized_supplier_ids):
        raise ValueError(
            "Multiple unscoped --api-key values must match the number of --supplier values"
        )

    return dict(zip(normalized_supplier_ids, unscoped_keys)), None


def resolve_supplier_api_key(
    supplier_id: str,
    *,
    scoped_api_keys: dict[str, str],
    default_api_key: str | None,
) -> str | None:
    """Return the effective API key for one supplier."""

    normalized_id = str(supplier_id or "").strip().lower()
    if not normalized_id:
        return default_api_key
    return scoped_api_keys.get(normalized_id, default_api_key)
