"""jBOM v3.0 Unified API

Provides simplified generate_bom() and generate_pos() functions with:
- Unified input= parameter (accepts both directories and specific files)
- Consistent output= parameter
- Auto-discovery of project files when given directories
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass

from jbom.generators.bom import BOMGenerator
from jbom.generators.pos import POSGenerator, PlacementOptions
from jbom.loaders.inventory import InventoryLoader
from jbom.processors.annotator import SchematicAnnotator
from jbom.common.generator import GeneratorOptions
from jbom.processors.inventory_matcher import InventoryMatcher


@dataclass
class BOMOptions:
    """Options for BOM generation"""

    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None
    fabricator: Optional[str] = None

    def to_generator_options(self):
        """Convert to GeneratorOptions"""
        from jbom.common.generator import GeneratorOptions

        opts = GeneratorOptions()
        opts.verbose = self.verbose
        opts.debug = self.debug
        opts.fields = self.fields
        opts.smd_only = self.smd_only  # Add as attribute
        opts.fabricator = self.fabricator  # Add as attribute
        return opts


@dataclass
class POSOptions:
    """Options for POS generation"""

    units: str = "mm"  # "mm" or "inch"
    origin: str = "board"  # "board" or "aux"
    smd_only: bool = True
    layer_filter: Optional[str] = None  # "TOP" or "BOTTOM"
    fields: Optional[List[str]] = None


def generate_bom(
    input: Union[str, Path],
    inventory: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
    output: Optional[Union[str, Path]] = None,
    options: Optional[BOMOptions] = None,
) -> Dict[str, Any]:
    """Generate Bill of Materials from KiCad schematic with inventory matching.

    Args:
        input: Path to KiCad project directory or .kicad_sch file
        inventory: Path(s) to inventory file(s) (.csv, .xlsx, .xls, or .numbers).
                  If None, inventory is generated from project components.
        output: Optional output path. If None, returns data without writing file.
                Special values: "-" or "stdout" for stdout, "console" for formatted table
        options: Optional BOMOptions for customization

    Returns:
        Dictionary containing:
        - components: List of Component objects
        - bom_entries: List of BOMEntry objects
        - inventory_count: Number of inventory items loaded
        - available_fields: Dictionary of available field names

    Examples:
        >>> # Auto-discover schematic in project directory
        >>> result = generate_bom(input="MyProject/", inventory="inventory.csv")

        >>> # Use specific schematic file
        >>> result = generate_bom(
        ...     input="MyProject/main.kicad_sch",
        ...     inventory="inventory.xlsx",
        ...     output="bom.csv"
        ... )

        >>> # Advanced options
        >>> opts = BOMOptions(verbose=True, debug=True, smd_only=True)
        >>> result = generate_bom(
        ...     input="MyProject/",
        ...     inventory="inventory.csv",
        ...     output="output/bom.csv",
        ...     options=opts
        ... )
    """
    opts = options or BOMOptions()

    # Verify inventory file(s) exist if provided
    inventory_paths = []
    if inventory:
        if isinstance(inventory, (str, Path)):
            paths = [inventory]
        else:
            paths = inventory

        for p in paths:
            path = Path(p)
            if not path.exists():
                raise FileNotFoundError(f"Inventory file not found: {path}")
            inventory_paths.append(path)

    # Load inventory and create matcher
    from jbom.processors.inventory_matcher import InventoryMatcher

    matcher = InventoryMatcher(inventory_paths if inventory_paths else None)

    # Create generator with matcher and options
    gen_opts = opts.to_generator_options()
    generator = BOMGenerator(matcher, gen_opts)

    # Run generator
    result = generator.run(input=input, output=output)

    return result


def back_annotate(
    project: Union[str, Path],
    inventory: Union[str, Path],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Back-annotate inventory data to KiCad schematic.

    Args:
        project: Path to KiCad project directory or .kicad_sch file
        inventory: Path to inventory file with updated data
        dry_run: If True, do not save changes to file

    Returns:
        Dictionary containing:
        - success: bool
        - updated_count: int
        - schematic_path: Path
        - updates: List[Dict] (details of updates)
        - error: str (if failed)
    """
    # 1. Discover Schematic
    matcher = InventoryMatcher(None)
    generator = BOMGenerator(matcher, GeneratorOptions())
    try:
        schematic_path = generator.discover_input(Path(project))
    except Exception as e:
        return {"success": False, "error": f"Error finding schematic: {e}"}

    if schematic_path.suffix != ".kicad_sch":
        return {
            "success": False,
            "error": f"Error: Back-annotation only supports .kicad_sch files. Found: {schematic_path}",
        }

    # 2. Load Inventory
    try:
        loader = InventoryLoader(Path(inventory))
        items, fields = loader.load()
    except Exception as e:
        return {"success": False, "error": f"Error loading inventory: {e}"}

    if not items:
        return {"success": False, "error": "Inventory is empty."}

    # 3. Load Annotator
    annotator = SchematicAnnotator(schematic_path)
    try:
        annotator.load()
    except Exception as e:
        return {
            "success": False,
            "error": f"Error loading schematic structure: {e}",
        }

    # 4. Iterate and Update
    component_count = 0
    update_details = []

    for item in items:
        if not item.uuid:
            continue

        # Prepare updates
        updates: Dict[str, str] = {}

        # Map Inventory Fields -> Schematic Properties
        if item.value:
            updates["Value"] = item.value
        if item.package:
            updates["Footprint"] = item.package
        if item.lcsc:
            updates["LCSC"] = item.lcsc
        if item.manufacturer:
            updates["Manufacturer"] = item.manufacturer
        if item.mfgpn:
            updates["MFGPN"] = item.mfgpn

        if not updates:
            continue

        # Split UUIDs (comma separated)
        uuids = [u.strip() for u in item.uuid.split(",") if u.strip()]

        for uuid in uuids:
            if annotator.update_component(uuid, updates):
                component_count += 1
                update_details.append({"uuid": uuid, "updates": updates})

    # 5. Save
    if annotator.modified and not dry_run:
        annotator.save()

    return {
        "success": True,
        "updated_count": component_count,
        "schematic_path": schematic_path,
        "updates": update_details,
        "modified": annotator.modified,
    }


def generate_pos(
    input: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    options: Optional[POSOptions] = None,
    loader_mode: str = "auto",
) -> Dict[str, Any]:
    """Generate component placement (POS/CPL) file from KiCad PCB.

    Args:
        input: Path to KiCad project directory or .kicad_pcb file
        output: Optional output path. If None, returns data without writing file.
                Special values: "-" or "stdout" for stdout, "console" for formatted table
        options: Optional POSOptions for customization
        loader_mode: PCB loading method: "auto", "pcbnew", or "sexp"

    Returns:
        Dictionary containing:
        - board: BoardModel object
        - entries: List of PcbComponent objects
        - component_count: Number of components
        - generator: POSGenerator instance for advanced usage

    Examples:
        >>> # Auto-discover PCB in project directory
        >>> result = generate_pos(input="MyProject/")

        >>> # Use specific PCB file
        >>> result = generate_pos(
        ...     input="MyProject/board.kicad_pcb",
        ...     output="pos.csv"
        ... )

        >>> # Advanced options
        >>> opts = POSOptions(
        ...     units="inch",
        ...     origin="aux",
        ...     smd_only=True,
        ...     layer_filter="TOP"
        ... )
        >>> result = generate_pos(
        ...     input="MyProject/",
        ...     output="output/pos.csv",
        ...     options=opts
        ... )
    """
    opts = options or POSOptions()

    # Create placement options from POSOptions
    placement_opts = PlacementOptions(
        units=opts.units,
        origin=opts.origin,
        smd_only=opts.smd_only,
        layer_filter=opts.layer_filter,
        loader_mode=loader_mode,
        fields=opts.fields,
    )

    # Create generator and run
    generator = POSGenerator(placement_opts)
    result = generator.run(input=input, output=output)

    return result
