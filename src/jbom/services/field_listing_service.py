"""Service API for namespace-aware field listing presentations.

This service centralizes list-fields matrix generation so CLI commands and
future Python integrations (for example plugin UIs) can share one contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jbom.common.fields import normalize_field_name


_NAMESPACE_PREFIXES: tuple[str, ...] = ("s", "p", "i", "a")


@dataclass(frozen=True)
class FieldNamespaceMatrixRow:
    """One row in the namespace matrix view for a canonical field name."""

    name: str
    s_token: str = ""
    p_token: str = ""
    i_token: str = ""
    a_token: str = ""

    def to_console_row(self) -> dict[str, str]:
        """Convert row to a console table mapping with fixed matrix columns."""

        return {
            "Name": self.name,
            "s:": self.s_token,
            "p:": self.p_token,
            "i:": self.i_token,
            "a:": self.a_token,
        }


@dataclass(frozen=True)
class FieldSourceRequirements:
    """Source requirements controlling namespace applicability."""

    require_sch: bool
    require_pcb: bool
    require_inv: bool


def is_namespace_applicable(
    namespace_prefix: str,
    *,
    requirements: FieldSourceRequirements,
) -> bool:
    """Return whether a namespace prefix is applicable for a source contract."""

    if namespace_prefix == "s":
        return requirements.require_sch
    if namespace_prefix == "p":
        return requirements.require_pcb
    if namespace_prefix == "i":
        return requirements.require_inv
    if namespace_prefix == "a":
        return True
    return True


class FieldListingService:
    """Build list-fields matrix data grouped by canonical field name."""

    def build_namespace_matrix(
        self,
        field_tokens: Iterable[str],
        *,
        requirements: FieldSourceRequirements | None = None,
    ) -> list[FieldNamespaceMatrixRow]:
        """Group available field tokens into Name|s:|p:|i:|c:|a: rows."""

        grouped: dict[str, dict[str, str]] = {}
        for raw_token in field_tokens:
            normalized_token = normalize_field_name(str(raw_token or ""))
            if not normalized_token:
                continue

            prefix, separator, remainder = normalized_token.partition(":")
            if separator and prefix in _NAMESPACE_PREFIXES and remainder:
                canonical_name = remainder
                slot = prefix
            else:
                canonical_name = normalized_token
                slot = "name"

            if (
                requirements is not None
                and slot in _NAMESPACE_PREFIXES
                and not is_namespace_applicable(slot, requirements=requirements)
            ):
                continue

            row = grouped.setdefault(
                canonical_name,
                {
                    "name": "",
                    "s": "",
                    "p": "",
                    "i": "",
                    "a": "",
                },
            )
            if not row[slot]:
                row[slot] = normalized_token

        matrix_rows: list[FieldNamespaceMatrixRow] = []
        for canonical_name in sorted(grouped.keys()):
            row = grouped[canonical_name]
            matrix_rows.append(
                FieldNamespaceMatrixRow(
                    name=row["name"] or canonical_name,
                    s_token=row["s"],
                    p_token=row["p"],
                    i_token=row["i"],
                    a_token=row["a"],
                )
            )
        return matrix_rows
