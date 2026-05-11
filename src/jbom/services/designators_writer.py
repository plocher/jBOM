"""Designators CSV generation service.

Produces ``designators.csv`` — one ``REFERENCE:COUNT`` line per unique
reference designator, sorted in natural (human) order.  This file is
consumed by downstream assembly tooling such as Fabrication-Toolkit.

Format example::

    C1:1
    C2:1
    R1:1
    U1:1

COUNT is the number of times the reference appears in the input list.
For correctly-annotated KiCad designs each designator is unique and the
count will always be ``1``, but the service handles duplicates
gracefully rather than raising an error.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from jbom.common.reference_sort import natural_reference_sort_key
from jbom.common.types import Diagnostic


@dataclass(frozen=True)
class DesignatorsResult:
    """Result produced by :class:`DesignatorsWriter`.

    Attributes:
        path: Path to the written ``designators.csv``, or ``None`` when
            the write was skipped (e.g. no references, or dry run).
        designator_count: Number of unique reference designators written.
        diagnostics: Ordered diagnostic messages from the write operation.
    """

    path: Path | None
    designator_count: int
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        if self.path is not None:
            object.__setattr__(self, "path", Path(self.path))
        object.__setattr__(self, "designator_count", int(self.designator_count))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))


class DesignatorsWriter:
    """Writes ``designators.csv`` from an iterable of reference designators.

    Typical usage::

        result = DesignatorsWriter.write(
            references=["R1", "C1", "U1", "R2"],
            output_path=production_dir / "designators.csv",
            force=True,
        )
    """

    @staticmethod
    def write(
        references: Iterable[str],
        output_path: Path,
        *,
        force: bool = False,
    ) -> DesignatorsResult:
        """Write ``designators.csv`` to *output_path*.

        Args:
            references: Iterable of reference designator strings.  May
                contain duplicates; occurrences are counted per designator.
                Empty or blank strings are silently skipped.
            output_path: Destination file path.
            force: When ``True`` overwrite an existing file.  When
                ``False`` and the file already exists, a warning diagnostic
                is returned and no file is written.

        Returns:
            :class:`DesignatorsResult` with the written path, count, and
            any diagnostics.
        """
        output_path = Path(output_path)
        diagnostics: list[Diagnostic] = []

        # Normalise and count
        counts: Counter[str] = Counter()
        for ref in references:
            ref = str(ref or "").strip()
            if ref:
                counts[ref] += 1

        if not counts:
            diagnostics.append(
                Diagnostic(
                    "info", "designators.csv skipped: no reference designators found"
                )
            )
            return DesignatorsResult(
                path=None,
                designator_count=0,
                diagnostics=tuple(diagnostics),
            )

        if output_path.exists() and not force:
            diagnostics.append(
                Diagnostic(
                    "warning",
                    f"designators.csv not written: '{output_path}' already exists "
                    "(use force=True to overwrite)",
                )
            )
            return DesignatorsResult(
                path=None,
                designator_count=len(counts),
                diagnostics=tuple(diagnostics),
            )

        # Sort naturally and write
        sorted_refs = sorted(counts.keys(), key=natural_reference_sort_key)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="\n") as fh:
            for ref in sorted_refs:
                fh.write(f"{ref}:{counts[ref]}\n")

        diagnostics.append(
            Diagnostic(
                "info",
                f"designators.csv written: {len(counts)} designator"
                f"{'s' if len(counts) != 1 else ''} → {output_path.name}",
            )
        )
        return DesignatorsResult(
            path=output_path,
            designator_count=len(counts),
            diagnostics=tuple(diagnostics),
        )


__all__ = [
    "DesignatorsResult",
    "DesignatorsWriter",
]
