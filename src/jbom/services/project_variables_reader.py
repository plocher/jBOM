"""Read ``text_variables`` from a KiCad ``.kicad_pro`` project file.

``.kicad_pro`` is JSON.  Among other things, it may carry a
``text_variables`` mapping that KiCad expands as ``${VAR_NAME}`` inside
title-block fields, schematic/PCB text, sheet titles, and friends.  This
module exposes that mapping as a typed jBOM artifact so consumers
(notably ``jbom.application.pcb_project_loader.ResolvedPcbProject`` and
downstream tools such as ``kproj``) no longer have to JSON-parse the
project file directly.

Per issue #332: *missing* ``text_variables`` is the modal case for
hand-edited or legacy projects, and is NOT a diagnostic \u2014 the artifact
just carries an empty map.  Bad inputs (missing file, wrong extension,
malformed JSON) raise so the caller can decide how to react.

The schematic and PCB title blocks are NOT consulted here; those are
read independently by :class:`jbom.services.schematic_reader.SchematicReader`
and :class:`jbom.services.pcb_reader.DefaultKiCadReaderService`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

__all__ = [
    "ProjectTextVariables",
    "read_text_variables",
]


@dataclass(frozen=True)
class ProjectTextVariables:
    """Typed view of the ``text_variables`` map from a ``.kicad_pro`` file.

    Attributes:
        variables:    Read-only mapping of variable name to value, both
                      strings.  Empty when the project file does not
                      declare ``text_variables`` or declares it as ``{}``
                      / ``null``.
        source_path:  The ``.kicad_pro`` path that was read.
    """

    variables: Mapping[str, str]
    source_path: Path


def _coerce_text_variables(raw: object) -> Mapping[str, str]:
    """Coerce a raw JSON ``text_variables`` value into a read-only ``str``\u2192``str`` map.

    Per the KiCad project schema, ``text_variables`` is a JSON object of
    string-to-string entries.  In the wild we still accept and skip
    non-string values defensively rather than crashing on a hand-edited
    project file; absence remains the modal case and is reported as an
    empty map.
    """
    if not isinstance(raw, dict):
        return MappingProxyType({})
    coerced: dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            coerced[key] = value
    return MappingProxyType(coerced)


def read_text_variables(project_file: Path) -> ProjectTextVariables:
    """Read ``text_variables`` from a ``.kicad_pro`` JSON project file.

    Args:
        project_file: Path to the KiCad project file (``*.kicad_pro``).

    Returns:
        A :class:`ProjectTextVariables` artifact.  When the project file
        does not declare ``text_variables``, the artifact carries an
        empty map; absence is intentional and emits no diagnostic.

    Raises:
        FileNotFoundError: When *project_file* does not exist.
        ValueError:        When *project_file* has the wrong suffix or
                           cannot be parsed as JSON.
    """
    if not project_file.exists():
        raise FileNotFoundError(f"Project file not found: {project_file}")
    if project_file.suffix.lower() != ".kicad_pro":
        raise ValueError(
            f"Expected .kicad_pro file, got: {project_file.suffix or '<none>'}"
        )
    try:
        payload = json.loads(project_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse project file as JSON: {project_file}: {exc}"
        ) from exc

    raw = payload.get("text_variables") if isinstance(payload, dict) else None
    return ProjectTextVariables(
        variables=_coerce_text_variables(raw),
        source_path=project_file,
    )
