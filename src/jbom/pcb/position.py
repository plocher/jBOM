"""Placement/CPL generation with column selection and presets."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Optional
import csv

from .model import BoardModel, PcbComponent
from ..common.fields import normalize_field_name, field_to_header
from ..common.packages import PackageType

Layer = Literal['TOP', 'BOTTOM']
Units = Literal['mm', 'inch']
Origin = Literal['board', 'aux']

PLACEMENT_FIELDS: Dict[str, str] = {
    'reference': 'Component reference designator',
    'x': 'X coordinate in selected units',
    'y': 'Y coordinate in selected units',
    'rotation': 'Rotation in degrees (top-view convention)',
    'side': 'Placement side (TOP/BOTTOM)',
    'footprint': 'Footprint name (lib:footprint)',
    'package': 'Package token (e.g., 0603, SOT-23, QFN)',
}

PLACEMENT_PRESETS: Dict[str, Dict[str, Optional[List[str]]]] = {
    'kicad_pos': {
        'fields': ['reference', 'x', 'y', 'rotation', 'side', 'footprint'],
        'description': 'KiCad-like POS columns',
    },
    'jlc': {
        'fields': ['reference', 'side', 'x', 'y', 'rotation', 'package'],
        'description': 'JLC-style CPL columns (headers not yet vendor-specific)',
    },
    'minimal': {
        'fields': ['reference', 'x', 'y', 'side'],
        'description': 'Just enough to locate components',
    },
    'all': {
        'fields': None,  # expand to all known placement fields
        'description': 'All placement fields',
    },
}



@dataclass
class PlacementOptions:
    units: Units = 'mm'
    origin: Origin = 'board'
    smd_only: bool = True
    layer_filter: Optional[Layer] = None


class PositionGenerator:
    def __init__(self, board: BoardModel, options: PlacementOptions = PlacementOptions()):
        self.board = board
        self.options = options

    # ---------------- column system ----------------
    def get_available_fields(self) -> Dict[str, str]:
        return dict(PLACEMENT_FIELDS)

    def _preset_fields(self, preset: str) -> List[str]:
        p = (preset or 'kicad_pos').lower()
        if p not in PLACEMENT_PRESETS:
            raise ValueError(f"Unknown preset: {preset} (valid: {', '.join(sorted(PLACEMENT_PRESETS))})")
        spec = PLACEMENT_PRESETS[p]
        if spec['fields'] is None:
            return list(PLACEMENT_FIELDS.keys())
        return list(spec['fields'])

    def parse_fields_argument(self, fields_arg: Optional[str]) -> List[str]:
        if not fields_arg:
            return self._preset_fields('kicad_pos')
        tokens = [t.strip() for t in fields_arg.split(',') if t.strip()]
        result: List[str] = []
        presets = set(PLACEMENT_PRESETS.keys())
        for tok in tokens:
            if tok.startswith('+'):
                name = tok[1:].lower()
                if name not in presets:
                    raise ValueError(f"Unknown preset: +{name} (valid: {', '.join('+'+p for p in sorted(presets))})")
                result.extend(self._preset_fields(name))
            else:
                n = normalize_field_name(tok)
                if n not in PLACEMENT_FIELDS:
                    raise ValueError(f"Unknown field: {tok}")
                result.append(n)
        # dedupe
        seen = set()
        deduped: List[str] = []
        for f in result:
            if f not in seen:
                seen.add(f)
                deduped.append(f)
        return deduped or self._preset_fields('kicad_pos')

    # ---------------- component iteration ----------------
    def iter_components(self) -> Iterable[PcbComponent]:
        comps = list(self.board.footprints)
        # smd filter (heuristic: keep when package token matches SMD list)
        if self.options.smd_only:
            smd = set(PackageType.SMD_PACKAGES)
            comps = [c for c in comps if (c.package_token and c.package_token in smd)]
        # layer filter
        if self.options.layer_filter:
            comps = [c for c in comps if c.side == self.options.layer_filter]
        return comps

    # ---------------- value helpers ----------------
    def _origin_offset_mm(self) -> tuple[float, float]:
        if self.options.origin == 'aux' and self.board.aux_origin_mm:
            return self.board.aux_origin_mm
        return (0.0, 0.0)

    def _xy_in_units(self, c: PcbComponent) -> tuple[float, float]:
        ox, oy = self._origin_offset_mm()
        x = c.center_x_mm - ox
        y = c.center_y_mm - oy
        if self.options.units == 'inch':
            return (x/25.4, y/25.4)
        return (x, y)

    # ---------------- CSV writers ----------------
    def write_csv(self, output_path: Path, fields: List[str]) -> None:
        """Write placement CSV to file or stdout.
        
        Special output_path values for stdout:
        - "-"
        - "console"
        - "stdout"
        """
        import sys
        
        norm_fields = [normalize_field_name(f) for f in fields]
        headers = [field_to_header(f) for f in norm_fields]
        
        # Check if output should go to stdout
        output_str = str(output_path)
        use_stdout = output_str in ('-', 'console', 'stdout')
        
        if use_stdout:
            f = sys.stdout
        else:
            f = open(output_path, 'w', newline='', encoding='utf-8')
        
        try:
            w = csv.writer(f)
            w.writerow(headers)
            for c in self.iter_components():
                row: List[str] = []
                x, y = self._xy_in_units(c)
                for fld in norm_fields:
                    if fld == 'reference':
                        row.append(c.reference)
                    elif fld == 'x':
                        row.append(f"{x:.4f}")
                    elif fld == 'y':
                        row.append(f"{y:.4f}")
                    elif fld == 'rotation':
                        row.append(f"{c.rotation_deg:.1f}")
                    elif fld == 'side':
                        row.append(c.side)
                    elif fld == 'footprint':
                        row.append(c.footprint_name)
                    elif fld == 'package':
                        row.append(c.package_token)
                    else:
                        row.append("")
                w.writerow(row)
        finally:
            if not use_stdout:
                f.close()

    # Convenience generators (still available)
    def generate_kicad_pos_rows(self) -> List[List[str]]:
        rows: List[List[str]] = []
        for c in self.iter_components():
            x, y = self._xy_in_units(c)
            rows.append([
                c.reference,
                round(x, 4),
                round(y, 4),
                round(c.rotation_deg, 1),
                c.side,
                c.footprint_name,
            ])
        return rows

    def generate_jlc_cpl_rows(self) -> List[List[str]]:
        rows: List[List[str]] = []
        for c in self.iter_components():
            x, y = self._xy_in_units(c)
            rows.append([
                c.reference,
                c.side,
                round(x, 4),
                round(y, 4),
                round(c.rotation_deg, 1),
                c.package_token,
            ])
        return rows
