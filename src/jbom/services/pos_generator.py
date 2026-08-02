"""POS (Position) file generation service.

This service generates component placement files from PCB data.
"""
from __future__ import annotations

import math
from typing import List, Tuple

from jbom.common.fields import normalize_field_name
from jbom.common.pcb_types import BoardModel, PadLocal, PcbComponent
from jbom.common.options import PlacementOptions
from jbom.common.reference_sort import natural_reference_sort_key


def local_to_board(
    local_x: float,
    local_y: float,
    anchor_x: float,
    anchor_y: float,
    rotation_deg: float,
) -> Tuple[float, float]:
    """Transform a footprint-local point into board millimetres.

    KiCad stores footprint-local pad coordinates relative to the footprint
    anchor and applies the footprint rotation with a Y-down board axis::

        board_x = anchor_x + lx * cos(θ) + ly * sin(θ)
        board_y = anchor_y - lx * sin(θ) + ly * cos(θ)
    """

    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    return (
        anchor_x + local_x * cos_t + local_y * sin_t,
        anchor_y - local_x * sin_t + local_y * cos_t,
    )


def pad_centers_bbox_board(
    pads: tuple[PadLocal, ...] | list[PadLocal],
    anchor_x: float,
    anchor_y: float,
    rotation_deg: float,
) -> Tuple[float, float]:
    """Return board-mm centre of the axis-aligned bbox of pad centres.

    Fabrication-Toolkit builds a pad bounding box via pcbnew pad geometry and
    takes its centre.  For equal-size pads this is equivalent to the bbox of
    pad centres; that is the pure-Python approximation used here.
    """

    if not pads:
        return anchor_x, anchor_y
    xs = [pad.x_mm for pad in pads]
    ys = [pad.y_mm for pad in pads]
    local_x = (min(xs) + max(xs)) / 2.0
    local_y = (min(ys) + max(ys)) / 2.0
    return local_to_board(local_x, local_y, anchor_x, anchor_y, rotation_deg)


def resolve_placement_xy(
    component: PcbComponent,
    *,
    position_mode: str,
) -> Tuple[float, float]:
    """Resolve board-mm placement XY for *component* under *position_mode*.

    Modes:
        - ``anchor``: footprint ``(at x y)``
        - ``pad_center``: pad-centre bbox when pads exist, else anchor
        - ``auto``: Fabrication-Toolkit rule — SMD uses anchor, non-SMD uses
          pad-centre bbox (falls back to anchor when no pads).  Footprint
          property ``FT Origin`` / ``Origin`` of ``Anchor`` or ``Center``
          overrides the package-type default.
    """

    mode = (position_mode or "anchor").strip().lower()
    origin_override = _origin_override(component)

    if mode == "anchor":
        use_center = False
    elif mode == "pad_center":
        use_center = bool(component.pads)
    else:  # auto
        if origin_override == "anchor":
            use_center = False
        elif origin_override == "center":
            use_center = bool(component.pads)
        else:
            use_center = (not _is_smd(component)) and bool(component.pads)

    if use_center:
        return pad_centers_bbox_board(
            component.pads,
            component.center_x_mm,
            component.center_y_mm,
            component.rotation_deg,
        )
    return component.center_x_mm, component.center_y_mm


def apply_origin_and_y(
    x_mm: float,
    y_mm: float,
    *,
    origin: str,
    y_direction: str,
    aux_origin_mm: tuple[float, float] | None,
) -> Tuple[float, float]:
    """Subtract place-file origin and optionally invert Y for CPL output.

    ``origin="aux"`` subtracts ``aux_origin_mm`` (defaulting to ``(0, 0)`` when
    unset, matching pcbnew ``GetAuxOrigin()``).  ``y_direction="down"`` applies
    the Fabrication-Toolkit / industry place-file Y flip after origin
    subtraction.
    """

    ox = oy = 0.0
    if (origin or "board").strip().lower() == "aux":
        if aux_origin_mm is not None:
            ox, oy = float(aux_origin_mm[0]), float(aux_origin_mm[1])
    x = x_mm - ox
    y = y_mm - oy
    if (y_direction or "up").strip().lower() == "down":
        y = -y
    return x, y


def rotate_offset(
    delta_x: float,
    delta_y: float,
    rotation_deg: float,
    *,
    side: str = "TOP",
) -> Tuple[float, float]:
    """Rotate a footprint-local XY offset into board/place-file space.

    Matches Fabrication-Toolkit ``process.py`` offset rotation for top/bottom.
    """

    theta = math.radians(rotation_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    if str(side or "TOP").upper().startswith("B"):
        return (
            delta_x * cos_t + delta_y * sin_t,
            delta_x * sin_t - delta_y * cos_t,
        )
    return (
        delta_x * cos_t - delta_y * sin_t,
        delta_x * sin_t + delta_y * cos_t,
    )


def _is_smd(component: PcbComponent) -> bool:
    mount = str(component.attributes.get("mount_type", "")).strip().lower()
    if mount in {"smd"}:
        return True
    if mount in {"through_hole", "through-hole", "tht"}:
        return False
    return str(component.attributes.get("smd", "")).strip().lower() in {
        "1",
        "true",
        "t",
        "yes",
        "y",
        "x",
    }


def _origin_override(component: PcbComponent) -> str | None:
    for key in ("FT Origin", "Origin", "ft_origin", "origin"):
        raw = component.attributes.get(key)
        if raw is None:
            continue
        token = str(raw).strip().capitalize()
        if token in {"Anchor", "Center"}:
            return token.lower()
    return None


class POSGenerator:
    """Service for generating position files from PCB data."""

    def __init__(self, options: PlacementOptions = None):
        """Initialize POS generator.

        Args:
            options: Placement generation options
        """
        self.options = options or PlacementOptions()

    def generate_pos_data(self, board: BoardModel) -> List[dict]:
        """Generate position data from board model.

        Args:
            board: Loaded PCB board model

        Returns:
            List of position entries
        """
        pos_entries = []

        for component in board.footprints:
            if self._should_include_component(component):
                normalized_attributes = self._normalize_component_attributes(
                    component.attributes
                )
                board_x, board_y = resolve_placement_xy(
                    component, position_mode=self.options.position_mode
                )
                place_x, place_y = apply_origin_and_y(
                    board_x,
                    board_y,
                    origin=self.options.origin,
                    y_direction=self.options.y_direction,
                    aux_origin_mm=board.aux_origin_mm,
                )
                # Only preserve raw tokens when they still match the emitted
                # coordinates (anchor mode, board origin, Y-up).
                use_raw = (
                    self.options.position_mode == "anchor"
                    and self.options.origin == "board"
                    and self.options.y_direction == "up"
                )
                entry = {
                    "reference": component.reference,
                    "x_mm": place_x,
                    "y_mm": place_y,
                    "rotation": component.rotation_deg,
                    "side": component.side,
                    "footprint": component.footprint_name,
                    "package": component.package_token,
                    # Raw tokens (if available) to preserve author-intended formatting
                    "x_raw": component.center_x_raw if use_raw else None,
                    "y_raw": component.center_y_raw if use_raw else None,
                    "rotation_raw": component.rotation_raw,
                }

                # Extract additional attributes that may be requested in field selection
                # Include value if available from component attributes
                if "Value" in component.attributes:
                    entry["value"] = component.attributes["Value"]
                elif hasattr(component, "value") and component.value:
                    entry["value"] = component.value
                else:
                    entry["value"] = ""

                # Include other common attributes that might be requested
                entry["fabricator_part_number"] = normalized_attributes.get(
                    "fabricator_part_number",
                    "",
                )
                for attribute_key, attribute_value in normalized_attributes.items():
                    entry.setdefault(attribute_key, attribute_value)

                pos_entries.append(entry)
        pos_entries.sort(
            key=lambda entry: natural_reference_sort_key(
                str(entry.get("reference", ""))
            )
        )

        return pos_entries

    def _should_include_component(self, component: PcbComponent) -> bool:
        """Determine if component should be included in position file."""
        # Apply SMD-only filter if requested
        if self.options.smd_only:
            mount_type = component.attributes.get("mount_type", "")
            if mount_type != "smd":
                return False

        # Apply layer filter if requested
        if self.options.layer_filter:
            if component.side.upper() != self.options.layer_filter:
                return False
        if self._is_excluded_from_position_files(component):
            return False

        return True

    def _is_excluded_from_position_files(self, component: PcbComponent) -> bool:
        """Return True if PCB metadata marks the component as position-file excluded."""

        normalized_attributes = self._normalize_component_attributes(
            component.attributes
        )
        return any(
            self._is_truthy_marker(normalized_attributes.get(flag_name))
            for flag_name in ("exclude_from_pos_files", "exclude_from_position_files")
        )

    @staticmethod
    def _is_truthy_marker(value: object) -> bool:
        """Return True when a marker value should be interpreted as enabled."""

        if isinstance(value, bool):
            return value
        normalized = str(value or "").strip().lower()
        if not normalized:
            return False
        return normalized in {"1", "true", "t", "yes", "y", "x"}

    @staticmethod
    def _normalize_component_attributes(attributes: dict[str, str]) -> dict[str, str]:
        """Normalize component attributes to canonical field IDs."""

        normalized: dict[str, str] = {}
        for key, value in attributes.items():
            normalized_key = normalize_field_name(key)
            if not normalized_key:
                continue
            normalized[normalized_key] = value

        return normalized
