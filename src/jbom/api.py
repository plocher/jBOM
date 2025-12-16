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


@dataclass
class BOMOptions:
    """Options for BOM generation"""

    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None

    def to_generator_options(self):
        """Convert to GeneratorOptions"""
        from jbom.common.generator import GeneratorOptions

        opts = GeneratorOptions()
        opts.verbose = self.verbose
        opts.debug = self.debug
        opts.fields = self.fields
        opts.smd_only = self.smd_only  # Add as attribute
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
    inventory: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    options: Optional[BOMOptions] = None,
) -> Dict[str, Any]:
    """Generate Bill of Materials from KiCad schematic with inventory matching.

    Args:
        input: Path to KiCad project directory or .kicad_sch file
        inventory: Path to inventory file (.csv, .xlsx, .xls, or .numbers)
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

    # Verify inventory file exists
    inventory_path = Path(inventory)
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {inventory_path}")

    # Load inventory and create matcher
    from jbom.processors.inventory_matcher import InventoryMatcher

    matcher = InventoryMatcher(inventory_path)

    # Create generator with matcher and options
    gen_opts = opts.to_generator_options()
    generator = BOMGenerator(matcher, gen_opts)

    # Run generator
    result = generator.run(input=input, output=output)

    return result


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
