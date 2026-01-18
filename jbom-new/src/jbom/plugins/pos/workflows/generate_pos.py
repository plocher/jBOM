"""POS generate workflow.

Composes KiCad reader + POS generator services to produce output.
Registered under name "pos.generate".
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from jbom.workflows import registry
from jbom.plugins.pos.services.pos_generator import create_pos_generator


def _generate_pos(pcb_file: Path, output: Optional[Union[Path, str]] = None) -> None:
    gen = create_pos_generator()
    gen.generate_pos_file(pcb_file=pcb_file, output_file=output)


# Register workflow at import time
registry.register("pos.generate", _generate_pos)
