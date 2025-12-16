"""jBOM v3.0 Unified API

Provides simplified generate_bom() and generate_pos() functions with:
- Unified input= parameter (accepts both directories and specific files)
- Consistent output= parameter
- Auto-discovery of project files when given directories
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass

from jbom.loaders.schematic import SchematicLoader
from jbom.loaders.pcb import load_board
from jbom.loaders.inventory import InventoryLoader
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.generators.bom import BOMGenerator
from jbom.generators.pos import POSGenerator, PlacementOptions
from jbom.common.utils import find_best_schematic, find_best_pcb
from jbom.common.types import Component, BOMEntry
from jbom.common.fields import parse_fields_argument


@dataclass
class BOMOptions:
    """Options for BOM generation"""
    verbose: bool = False
    debug: bool = False
    smd_only: bool = False
    fields: Optional[List[str]] = None


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
    
    # Convert to Path objects
    input_path = Path(input)
    inventory_path = Path(inventory)
    output_path = Path(output) if output else None
    
    # Auto-discover schematic if input is a directory
    if input_path.is_dir():
        schematic_path = find_best_schematic(input_path)
        if not schematic_path:
            raise FileNotFoundError(f"No .kicad_sch file found in {input_path}")
    else:
        schematic_path = input_path
        if not schematic_path.exists():
            raise FileNotFoundError(f"Schematic file not found: {schematic_path}")
    
    # Verify inventory file exists
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory file not found: {inventory_path}")
    
    # Load schematic
    loader = SchematicLoader(schematic_path)
    components = loader.parse()
    
    # Load inventory and create matcher
    matcher = InventoryMatcher(inventory_path)
    
    # Generate BOM
    generator = BOMGenerator(components, matcher)
    bom_entries, excluded_count, debug_diagnostics = generator.generate_bom(
        verbose=opts.verbose,
        debug=opts.debug,
        smd_only=opts.smd_only
    )
    
    # Get available fields
    available_fields = generator.get_available_fields(components)
    
    # Write output if specified
    if output_path:
        output_str = str(output_path).lower()
        if output_str in ("-", "stdout"):
            # CSV to stdout
            any_notes = any((e.notes or "").strip() for e in bom_entries)
            fields = opts.fields or parse_fields_argument(
                "+standard", available_fields, include_verbose=opts.verbose, any_notes=any_notes
            )
            generator.write_bom_csv(bom_entries, Path("-"), fields)
        elif output_str == "console":
            # Formatted table (handled by caller, not here)
            pass
        else:
            # Write to file
            any_notes = any((e.notes or "").strip() for e in bom_entries)
            fields = opts.fields or parse_fields_argument(
                "+standard", available_fields, include_verbose=opts.verbose, any_notes=any_notes
            )
            generator.write_bom_csv(bom_entries, output_path, fields)
    
    return {
        "components": components,
        "bom_entries": bom_entries,
        "inventory_count": len(matcher.inventory),
        "available_fields": available_fields,
        "generator": generator,  # For advanced usage
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
        - rows: List of position data rows
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
    
    # Convert to Path objects
    input_path = Path(input)
    output_path = Path(output) if output else None
    
    # Auto-discover PCB if input is a directory
    if input_path.is_dir():
        pcb_path = find_best_pcb(input_path)
        if not pcb_path:
            raise FileNotFoundError(f"No .kicad_pcb file found in {input_path}")
    else:
        pcb_path = input_path
        if not pcb_path.exists():
            raise FileNotFoundError(f"PCB file not found: {pcb_path}")
    
    # Load board
    board = load_board(pcb_path, mode=loader_mode)
    
    # Create placement options
    placement_opts = PlacementOptions(
        units=opts.units,
        origin=opts.origin,
        smd_only=opts.smd_only,
        layer_filter=opts.layer_filter,
    )
    
    # Generate position data
    generator = POSGenerator(board, placement_opts)
    rows = generator.generate_kicad_pos_rows()
    
    # Write output if specified
    if output_path:
        output_str = str(output_path).lower()
        if output_str not in ("console",):  # console handled by caller
            fields = opts.fields or generator.parse_fields_argument("+standard")
            generator.write_csv(output_path, fields)
    
    return {
        "board": board,
        "rows": rows,
        "generator": generator,  # For advanced usage
    }
