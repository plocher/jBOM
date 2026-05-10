"""Rotation and centroid-offset correction service for CPL (pick-and-place) generation.

KiCad's footprint orientation convention does not always match what fabrication
houses (notably JLCPCB) expect.  This service applies a database of per-footprint
delta rotations and XY offsets so that the generated CPL file matches the
fabricator's assembly convention.

The correction database (``transformations.csv``) is harvested from the
Fabrication-Toolkit project (https://github.com/bennymeg/Fabrication-Toolkit)
under its MIT License.  Users can override or extend it by placing a custom
``transformations.csv`` in ``~/.jbom/`` or ``<project>/.jbom/`` — that file
takes precedence over the built-in one.

Matching semantics (first-match wins, same as Fabrication-Toolkit):
    - If the pattern contains ``:``, it is matched against the full
      ``LIBRARY:NAME`` footprint string.
    - If the pattern contains no ``:``, it is matched against the NAME
      part only (right side of ``:``, or the whole string if no ``:`` present).
    - Matching is performed with ``re.search()`` — patterns can be anchored
      with ``^`` / ``$`` for precision.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

_BUILTIN_TRANSFORMATIONS = (
    Path(__file__).parent.parent / "config" / "transformations.csv"
)

_TRANSFORMATIONS_FILENAME = "transformations.csv"


@dataclass
class CorrectionRule:
    """One row from the transformations database.

    Attributes:
        pattern: Raw regex string as read from the CSV.
        rotation: Delta degrees to add to KiCad rotation.
        delta_x: Millimetre offset to add to centroid X.
        delta_y: Millimetre offset to add to centroid Y.
    """

    pattern: str
    rotation: float
    delta_x: float
    delta_y: float

    def __post_init__(self) -> None:
        # Compile the regex eagerly; stored as a plain attribute (not a field)
        # so dataclass equality / hashing are based on the string pattern only.
        self._compiled: re.Pattern = re.compile(self.pattern)

    @property
    def compiled(self) -> re.Pattern:
        """Compiled regex for this rule's pattern."""
        return self._compiled


class RotationCorrectionService:
    """Applies footprint-specific rotation and centroid offsets for CPL output.

    Loads a ``transformations.csv`` database and uses first-match regex
    semantics to return delta corrections for any given footprint name.

    Typical usage::

        service = RotationCorrectionService.load()
        corrected_rotation = service.apply_rotation("Capacitor_SMD:CP_Elec_5x5", 90.0)
        dx, dy = service.apply_offset("Capacitor_SMD:CP_Elec_5x5")
    """

    def __init__(self, rules: list[CorrectionRule]) -> None:
        self._rules = list(rules)

    # ------------------------------------------------------------------
    # Class-level factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        *,
        cwd: Path | None = None,
        transformations_path: Path | None = None,
    ) -> RotationCorrectionService:
        """Load a :class:`RotationCorrectionService` from the correction database.

        The search order follows the jBOM profile search path (highest priority
        first), falling back to the built-in ``transformations.csv``.  Pass
        ``transformations_path`` to bypass the search entirely and load from a
        specific file (useful for tests).

        Args:
            cwd: Working directory override for the profile search.  Defaults
                to ``Path.cwd()``.
            transformations_path: Explicit path to a ``transformations.csv``
                file.  When provided, the profile search path is skipped.

        Returns:
            :class:`RotationCorrectionService` loaded with the discovered rules.

        Raises:
            FileNotFoundError: When no ``transformations.csv`` can be found.
            RuntimeError: When the CSV file contains unparseable data.
        """
        if transformations_path is not None:
            resolved = Path(transformations_path)
        else:
            resolved = cls._find_transformations_csv(cwd=cwd)

        rules = cls._parse_csv(resolved)
        return cls(rules)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def rule_count(self) -> int:
        """Number of correction rules loaded."""
        return len(self._rules)

    def apply_rotation(
        self,
        footprint: str,
        rotation: float,
        *,
        convention: str | None = None,
    ) -> float:
        """Return the corrected rotation for *footprint*.

        Args:
            footprint: Full ``LIBRARY:NAME`` footprint identifier as stored
                in the KiCad PCB file.
            rotation: Original KiCad rotation in degrees.
            convention: Named angle convention from the fabricator's
                ``.fab.yaml`` ``rotation_convention`` key.  Known values:

                * ``None`` (default) — return the raw delta-adjusted value;
                  KiCad's native angle range is preserved.
                * ``"jlcpcb"`` — fold the result into ``[0°, 360°)``;
                  JLCPCB's assembler does not accept negative angles.

                Unrecognised convention strings are treated the same as
                ``None`` (raw output) to preserve forward compatibility.

        Returns:
            Corrected rotation in the angle convention specified by
            *convention*, or the raw delta-adjusted value when *convention*
            is ``None`` or unrecognised.
        """
        rule = self._match_rule(footprint)
        delta = rule.rotation if rule is not None else 0.0
        result = rotation + delta
        if convention == "jlcpcb":
            return result % 360.0
        return result

    def apply_offset(self, footprint: str) -> tuple[float, float]:
        """Return the ``(delta_x, delta_y)`` centroid correction for *footprint*.

        Args:
            footprint: Full ``LIBRARY:NAME`` footprint identifier.

        Returns:
            ``(delta_x_mm, delta_y_mm)`` tuple.  Returns ``(0.0, 0.0)`` when
            no rule matches.
        """
        rule = self._match_rule(footprint)
        if rule is None:
            return (0.0, 0.0)
        return (rule.delta_x, rule.delta_y)

    def has_correction(self, footprint: str) -> bool:
        """Return ``True`` when at least one rule matches *footprint*."""
        return self._match_rule(footprint) is not None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_rule(self, footprint: str) -> CorrectionRule | None:
        """Return the first rule whose pattern matches *footprint*, or ``None``.

        Matching logic mirrors Fabrication-Toolkit:
        - Pattern with ``:``: searched against the full LIBRARY:NAME string.
        - Pattern without ``:``: searched against the NAME part only.
        """
        footprint_str = str(footprint or "")
        if ":" in footprint_str:
            name_only = footprint_str.split(":", 1)[1]
        else:
            name_only = footprint_str

        for rule in self._rules:
            if ":" in rule.pattern:
                check = footprint_str
            else:
                check = name_only
            if rule.compiled.search(check):
                return rule
        return None

    # ------------------------------------------------------------------
    # CSV parsing
    # ------------------------------------------------------------------

    @classmethod
    def _find_transformations_csv(cls, *, cwd: Path | None = None) -> Path:
        """Return the first ``transformations.csv`` found on the search path.

        Searches user-configurable locations (via :func:`profile_search_dirs`)
        before falling back to the built-in package file.
        """
        from jbom.config.profile_search import profile_search_dirs

        for directory in profile_search_dirs(cwd=cwd):
            candidate = directory / _TRANSFORMATIONS_FILENAME
            if candidate.is_file():
                return candidate

        # Fall back to built-in
        if _BUILTIN_TRANSFORMATIONS.is_file():
            return _BUILTIN_TRANSFORMATIONS

        raise FileNotFoundError(
            f"No {_TRANSFORMATIONS_FILENAME!r} found in search path or built-in "
            f"package directory ({_BUILTIN_TRANSFORMATIONS.parent})"
        )

    @classmethod
    def _parse_csv(cls, path: Path) -> list[CorrectionRule]:
        """Parse *path* and return an ordered list of :class:`CorrectionRule`."""
        rules: list[CorrectionRule] = []
        with open(path, newline="", encoding="utf-8") as fh:
            for line_no, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                # Skip blank lines and comment lines (start with '#')
                if not line or line.startswith("#"):
                    continue
                # Parse individual CSV row
                row = next(csv.reader([line]))
                if len(row) < 2:
                    continue
                pattern_raw = row[0].strip()
                # Skip the header row (first data column is literally the word
                # "Regex To Match" or similar)
                if pattern_raw.lower() in {"regex to match", "pattern", "footprint"}:
                    continue
                try:
                    rotation = float(row[1]) if row[1].strip() else 0.0
                    delta_x = float(row[2]) if len(row) > 2 and row[2].strip() else 0.0
                    delta_y = float(row[3]) if len(row) > 3 and row[3].strip() else 0.0
                except ValueError as exc:
                    raise RuntimeError(
                        f"{path}:{line_no}: non-numeric value in correction row: {exc}"
                    ) from exc
                try:
                    rule = CorrectionRule(
                        pattern=pattern_raw,
                        rotation=rotation,
                        delta_x=delta_x,
                        delta_y=delta_y,
                    )
                except re.error as exc:
                    raise RuntimeError(
                        f"{path}:{line_no}: invalid regex pattern {pattern_raw!r}: {exc}"
                    ) from exc
                rules.append(rule)
        return rules


__all__ = [
    "CorrectionRule",
    "RotationCorrectionService",
]
