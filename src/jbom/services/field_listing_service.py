"""Service API for namespace-aware field listing presentations.

This service centralizes list-fields matrix generation so CLI commands and
future Python integrations (for example plugin UIs) can share one contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jbom.common.fields import normalize_field_name


_NAMESPACE_PREFIXES: tuple[str, ...] = ("s", "p", "i", "c", "a")


@dataclass(frozen=True)
class FieldNamespaceMatrixRow:
    """One row in the namespace matrix view for a canonical field name."""

    name: str
    s_token: str = ""
    p_token: str = ""
    i_token: str = ""
    c_token: str = ""
    a_token: str = ""

    def to_console_row(self) -> dict[str, str]:
        """Convert row to a console table mapping with fixed matrix columns."""

        return {
            "Name": self.name,
            "s:": self.s_token,
            "p:": self.p_token,
            "i:": self.i_token,
            "c:": self.c_token,
            "a:": self.a_token,
        }


class FieldListingService:
    """Build list-fields matrix data grouped by canonical field name."""

    def build_namespace_matrix(
        self,
        field_tokens: Iterable[str],
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

            row = grouped.setdefault(
                canonical_name,
                {
                    "name": "",
                    "s": "",
                    "p": "",
                    "i": "",
                    "c": "",
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
                    c_token=row["c"],
                    a_token=row["a"],
                )
            )
        return matrix_rows
