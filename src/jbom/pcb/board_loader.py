"""Load KiCad .kicad_pcb into BoardModel with pcbnew→S-expression fallback."""
from __future__ import annotations
from pathlib import Path
from typing import Optional, List

from .model import BoardModel, PcbComponent
from ..common.packages import PackageType


class BoardLoader:
    def __init__(self, board_path: Path, mode: str = "auto"):
        self.board_path = Path(board_path)
        self.mode = mode  # 'auto' | 'pcbnew' | 'sexp'

    def load(self) -> BoardModel:
        """Load board via selected mode.
        - auto: pcbnew if importable; else S-expression
        - pcbnew: require pcbnew, else raise ImportError
        - sexp: always use S-expression parser
        """
        if self.mode not in ("auto", "pcbnew", "sexp"):
            raise ValueError("mode must be one of: auto|pcbnew|sexp")
        if self.mode in ("auto", "pcbnew"):
            try:
                return self._load_with_pcbnew()
            except Exception:
                if self.mode == "pcbnew":
                    raise
        return self._load_with_sexp()

    # -------------------- pcbnew path --------------------
    def _load_with_pcbnew(self) -> BoardModel:
        import importlib
        pcbnew = importlib.import_module("pcbnew")  # raises ImportError if unavailable
        brd = pcbnew.LoadBoard(str(self.board_path))

        board = BoardModel(path=self.board_path)
        # Origins (optional; may be None)
        try:
            aux = brd.GetAuxOrigin()
            board.aux_origin_mm = (pcbnew.ToMM(aux.x), pcbnew.ToMM(aux.y))
        except Exception:
            board.aux_origin_mm = None
        try:
            ori = brd.GetDesignSettings().GetGridOrigin()
            board.board_origin_mm = (pcbnew.ToMM(ori.x), pcbnew.ToMM(ori.y))
        except Exception:
            board.board_origin_mm = None
        try:
            board.kicad_version = getattr(pcbnew, "GetBuildVersion", lambda: None)()
        except Exception:
            board.kicad_version = None

        for fp in brd.GetFootprints():
            ref = fp.GetReference()
            # Footprint name (lib:footprint)
            try:
                fpid = fp.GetFPID()
                try:
                    fp_name = fpid.AsString()
                except Exception:
                    # Compose best-effort name
                    lib = getattr(fpid, "GetLibNickname", lambda: "")()
                    name = getattr(fpid, "GetLibItemName", lambda: "")()
                    fp_name = f"{lib}:{name}" if lib or name else str(fpid)
            except Exception:
                fp_name = getattr(fp, "GetFPIDAsString", lambda: fp.GetValue())()

            # Position in mm
            pos = fp.GetPosition()
            try:
                x_mm = pcbnew.ToMM(pos.x)
                y_mm = pcbnew.ToMM(pos.y)
            except Exception:
                x_mm = float(pos.x)
                y_mm = float(pos.y)

            # Rotation
            rot = 0.0
            if hasattr(fp, "GetOrientationDegrees"):
                rot = float(fp.GetOrientationDegrees())
            else:
                try:
                    rot = float(fp.GetOrientation()) / 10.0
                except Exception:
                    rot = 0.0

            # Side
            side = "BOTTOM" if getattr(fp, "IsFlipped", lambda: False)() else "TOP"
            
            # Extract attributes (datasheet, version, SMD type)
            attributes = {}
            
            # Get properties
            try:
                # Try to get properties (KiCad 7+)
                if hasattr(fp, 'GetProperties'):
                    props = fp.GetProperties()
                    for key, val in props.items():
                        if isinstance(key, str) and isinstance(val, str):
                            attributes[key.lower()] = val
            except Exception:
                pass
            
            # Get datasheet
            try:
                if hasattr(fp, 'GetDatasheet'):
                    ds = fp.GetDatasheet()
                    if ds:
                        attributes['datasheet'] = ds
            except Exception:
                pass
            
            # Get SMD type from footprint attributes
            try:
                if hasattr(fp, 'GetAttributes'):
                    attrs = fp.GetAttributes()
                    # attrs is typically an integer flag
                    # FP_SMD = 1, FP_THROUGH_HOLE = 2
                    if attrs == 1 or (hasattr(fp, 'IsSMD') and fp.IsSMD()):
                        attributes['smd'] = 'SMD'
                    elif attrs == 2:
                        attributes['smd'] = 'PTH'
            except Exception:
                pass

            pkg = self._extract_package_token(fp_name)
            board.footprints.append(
                PcbComponent(
                    reference=ref,
                    footprint_name=fp_name,
                    package_token=pkg,
                    center_x_mm=x_mm,
                    center_y_mm=y_mm,
                    rotation_deg=rot,
                    side=side,
                    attributes=attributes,
                )
            )
        return board

    # -------------------- S-expression path --------------------
    def _load_with_sexp(self) -> BoardModel:
        from ..common.sexp_parser import load_kicad_file, walk_nodes

        sexp = load_kicad_file(self.board_path)
        board = BoardModel(path=self.board_path)

        for footprint_node in walk_nodes(sexp, "footprint"):
            comp = self._parse_footprint_node(footprint_node)
            if comp:
                board.footprints.append(comp)

        return board

    def _parse_footprint_node(self, node) -> Optional[PcbComponent]:
        from sexpdata import Symbol

        # node: (footprint "Lib:Name" (layer "F.Cu") (at x y [rot]) (fp_text reference "R1" ... ) ...)
        fp_name = None
        if len(node) >= 2 and isinstance(node[1], str):
            fp_name = node[1]
        ref = None
        x_mm = y_mm = 0.0
        rot = 0.0
        side = "TOP"
        attributes = {}
        datasheet = ""
        version = ""
        smd_type = ""

        for child in node[2:]:
            if not (isinstance(child, list) and child):
                continue
            head = child[0]
            if head == Symbol("layer") and len(child) >= 2 and isinstance(child[1], str):
                side = "TOP" if child[1].startswith("F.") else ("BOTTOM" if child[1].startswith("B.") else side)
            elif head == Symbol("at"):
                # (at x y [rot])
                if len(child) >= 3:
                    try:
                        x_mm = float(child[1])
                        y_mm = float(child[2])
                    except Exception:
                        pass
                if len(child) >= 4:
                    try:
                        rot = float(child[3])
                    except Exception:
                        pass
            elif head == Symbol("fp_text") and len(child) >= 3:
                # (fp_text reference "R1" ...)
                if child[1] == Symbol("reference") and isinstance(child[2], str):
                    ref = child[2]
            elif head == Symbol("property") and len(child) >= 3:
                # (property "Reference" "R1" ... ) or (property "Datasheet" "url" ...)
                try:
                    key = child[1]
                    val = child[2]
                    if isinstance(key, str) and isinstance(val, str):
                        if key == "Reference":
                            ref = val
                        elif key == "Datasheet":
                            datasheet = val
                        elif key == "ki_version":
                            version = val
                        else:
                            # Store other properties in attributes
                            attributes[key] = val
                except Exception:
                    pass
            elif head == Symbol("attr"):
                # (attr smd) or (attr through_hole) or (attr board_only)
                # This indicates the footprint type
                if len(child) >= 2:
                    attr_type = str(child[1])
                    if attr_type in ('smd', 'through_hole', 'board_only', 'exclude_from_pos_files', 'exclude_from_bom'):
                        if attr_type == 'smd':
                            smd_type = 'SMD'
                        elif attr_type == 'through_hole':
                            smd_type = 'PTH'

        if not ref:
            return None
        pkg = self._extract_package_token(fp_name or "")
        
        comp = PcbComponent(
            reference=ref,
            footprint_name=fp_name or "",
            package_token=pkg,
            center_x_mm=x_mm,
            center_y_mm=y_mm,
            rotation_deg=rot,
            side=side,
            attributes=attributes,
        )
        
        # Add extracted fields to attributes for easy access
        if datasheet:
            comp.attributes['datasheet'] = datasheet
        if version:
            comp.attributes['version'] = version
        if smd_type:
            comp.attributes['smd'] = smd_type
        
        return comp

    # -------------------- helpers --------------------
    def _extract_package_token(self, footprint_name: str) -> str:
        fp = (footprint_name or "").lower()
        for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
            if pattern in fp:
                return pattern
        return ""


def load_board(board_path: Path, *, mode: str = "auto") -> BoardModel:
    return BoardLoader(board_path, mode=mode).load()
