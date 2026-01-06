"""jBOM v3.0 Unified API

Provides simplified generate_bom() and generate_pos() functions with:
- Unified input= parameter (accepts both directories and specific files)
- Consistent output= parameter
- Auto-discovery of project files when given directories
"""

from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Set
from dataclasses import dataclass, field

from jbom.generators.bom import BOMGenerator
from jbom.generators.pos import POSGenerator, PlacementOptions
from jbom.loaders.inventory import InventoryLoader
from jbom.processors.annotator import SchematicAnnotator
from jbom.common.generator import GeneratorOptions
from jbom.processors.inventory_matcher import InventoryMatcher
from jbom.processors.inventory_enricher import InventoryEnricher
from jbom.search import SearchResult
from jbom.search.mouser import MouserProvider
from jbom.search.filter import SearchFilter


@dataclass
class BOMOptions:
    """Options for BOM generation"""

    verbose: bool = False
    debug: bool = False
    debug_categories: Set[str] = field(default_factory=set)
    smd_only: bool = False
    fields: Optional[List[str]] = None
    fabricator: Optional[str] = None

    def to_generator_options(self):
        """Convert to GeneratorOptions"""
        from jbom.common.generator import GeneratorOptions

        opts = GeneratorOptions()
        opts.verbose = self.verbose
        opts.debug = self.debug
        opts.debug_categories = self.debug_categories
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
    fabricator: Optional[str] = None


@dataclass
class InventoryOptions:
    """Options for inventory generation with search enrichment"""

    # Search options
    search: bool = False
    provider: str = "mouser"
    api_key: Optional[str] = None
    limit: int = 1
    interactive: bool = False

    # Output options
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


def search_parts(
    query: str,
    provider: str = "mouser",
    limit: int = 10,
    api_key: Optional[str] = None,
    filter_parametric: bool = True,
) -> List[SearchResult]:
    """Search for parts from external distributors.

    Args:
        query: Search query (keyword, part number, etc.)
        provider: Provider name (default: "mouser")
        limit: Maximum results to return
        api_key: Optional API key (overrides environment)
        filter_parametric: Enable smart parametric filtering

    Returns:
        List of SearchResult objects
    """
    if provider == "mouser":
        prov = MouserProvider(api_key=api_key)
    else:
        raise ValueError(
            f"Unsupported search provider: '{provider}'. "
            f"Currently supported providers: 'mouser'."
        )

    results = prov.search(query, limit=limit)

    if filter_parametric:
        results = SearchFilter.filter_by_query(results, query)

    return results


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


def generate_enriched_inventory(
    *,
    input: Union[str, Path],
    output: Optional[Union[str, Path]] = None,
    options: Optional[InventoryOptions] = None,
) -> Dict[str, Any]:
    """Generate enriched inventory with automated search integration.

    Args:
        input: Path to KiCad project directory or .kicad_sch file
        output: Optional output path. If None, returns data without writing file.
                Special values: "-" or "stdout" for stdout, "console" for formatted table
        options: Optional InventoryOptions for customization

    Returns:
        Dictionary containing:
        - inventory_items: List of InventoryItem objects
        - field_names: List of field names
        - component_count: Number of components processed
        - search_stats: Search statistics (if search enabled)
        - components: Original Component objects

    Examples:
        >>> # Basic inventory generation (no search)
        >>> result = generate_enriched_inventory(input="MyProject/")

        >>> # With search enrichment
        >>> opts = InventoryOptions(search=True, provider="mouser", limit=1)
        >>> result = generate_enriched_inventory(
        ...     input="MyProject/",
        ...     output="enriched_inventory.csv",
        ...     options=opts
        ... )

        >>> # Multiple candidates per component
        >>> opts = InventoryOptions(
        ...     search=True,
        ...     provider="mouser",
        ...     limit=3,
        ...     api_key="your_key"
        ... )
        >>> result = generate_enriched_inventory(input="MyProject/", options=opts)
    """
    opts = options or InventoryOptions()

    # 1. Load components from project
    # Use BOMGenerator's input discovery logic
    matcher = InventoryMatcher(None)
    generator = BOMGenerator(matcher, GeneratorOptions())

    try:
        input_path = generator.discover_input(Path(input))
        components = generator.load_input(input_path)
    except Exception as e:
        return {
            "success": False,
            "error": f"Error loading project: {e}",
            "inventory_items": [],
            "field_names": [],
            "component_count": 0,
            "search_stats": {},
        }

    if not components:
        return {
            "success": False,
            "error": "No components found in project.",
            "inventory_items": [],
            "field_names": [],
            "component_count": 0,
            "search_stats": {},
        }

    # 2. Generate inventory (with or without search enrichment)
    if opts.search:
        # Create search provider
        if opts.provider == "mouser":
            try:
                search_provider = MouserProvider(api_key=opts.api_key)
            except ValueError as e:
                return {
                    "success": False,
                    "error": f"Search provider error: {e}",
                    "inventory_items": [],
                    "field_names": [],
                    "component_count": 0,
                    "search_stats": {},
                }
        else:
            return {
                "success": False,
                "error": (
                    f"Unsupported search provider: '{opts.provider}'. "
                    f"Currently supported providers: 'mouser'."
                ),
                "inventory_items": [],
                "field_names": [],
                "component_count": 0,
                "search_stats": {},
            }

        # Use InventoryEnricher for search-enhanced generation
        enricher = InventoryEnricher(
            components=components,
            search_provider=search_provider,
            limit=opts.limit,
            interactive=opts.interactive,
        )

        try:
            inventory_items, field_names = enricher.enrich()

            search_stats = {
                "searches_performed": enricher.search_count,
                "successful_searches": enricher.successful_searches,
                "failed_searches": enricher.failed_searches,
                "provider": opts.provider,
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error during search enrichment: {e}",
                "inventory_items": [],
                "field_names": [],
                "component_count": 0,
                "search_stats": {},
            }
    else:
        # Use ProjectInventoryLoader for basic inventory generation
        from jbom.loaders.project_inventory import ProjectInventoryLoader

        loader = ProjectInventoryLoader(components)
        inventory_items, field_names = loader.load()

        search_stats = {"search_enabled": False}

    # 3. Handle output
    if output:
        try:
            _write_inventory_output(inventory_items, field_names, output)
        except Exception as e:
            return {
                "success": False,
                "error": f"Error writing output: {e}",
                "inventory_items": inventory_items,
                "field_names": field_names,
                "component_count": len(components),
                "search_stats": search_stats,
            }

    return {
        "success": True,
        "inventory_items": inventory_items,
        "field_names": field_names,
        "component_count": len(components),
        "search_stats": search_stats,
        "components": components,
    }


def _write_inventory_output(
    inventory_items: List[Any], field_names: List[str], output: Union[str, Path]
) -> None:
    """Write inventory items to specified output format."""
    import sys

    output_str = str(output)

    if output_str in ["-", "stdout"]:
        # Write to stdout
        _write_inventory_csv(inventory_items, field_names, sys.stdout)
    elif output_str == "console":
        # Print formatted table to console
        _print_inventory_table(inventory_items, field_names)
    else:
        # Write to file
        output_path = Path(output)
        output_str = str(output)
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            # Re-raise with original output path for better error message
            raise PermissionError(f"[Errno 13] Permission denied: '{output_str}'") from e
        
        try:
            with open(output_path, "w", newline="", encoding="utf-8") as f:
                _write_inventory_csv(inventory_items, field_names, f)
        except PermissionError as e:
            # Re-raise with original output path for better error message
            raise PermissionError(f"[Errno 13] Permission denied: '{output_str}'") from e


def _write_inventory_csv(
    inventory_items: List[Any], field_names: List[str], file
) -> None:
    """Write inventory items as CSV."""
    import csv

    writer = csv.writer(file)
    writer.writerow(field_names)

    for item in inventory_items:
        row = []
        for field_name in field_names:
            # Get value from item attribute or raw_data
            val = ""
            field_lower = field_name.lower()
            if hasattr(item, field_lower):
                val = getattr(item, field_lower)
            elif (
                hasattr(item, "raw_data")
                and item.raw_data
                and field_name in item.raw_data
            ):
                val = item.raw_data[field_name]
            elif field_name == "UUID":
                val = getattr(item, "uuid", "")
            elif field_name == "Distributor_Part_Number":
                val = getattr(item, "distributor_part_number", "")
            row.append(str(val) if val is not None else "")
        writer.writerow(row)


def _print_inventory_table(inventory_items: List[Any], field_names: List[str]) -> None:
    """Print inventory items as formatted table."""
    if not inventory_items:
        print("No inventory items found.")
        return

    # Select key fields for console display
    display_fields = [
        "IPN",
        "Value",
        "Package",
        "Category",
        "Manufacturer",
        "MFGPN",
        "Priority",
    ]
    available_fields = [f for f in display_fields if f in field_names]

    if not available_fields:
        available_fields = field_names[:6]  # Show first 6 fields

    print(f"Generated {len(inventory_items)} inventory items:")
    print("-" * 100)

    # Print header
    header = " | ".join(f"{field:<15}" for field in available_fields)
    print(header)
    print("-" * len(header))

    # Print rows
    for item in inventory_items[:20]:  # Limit to 20 rows for console
        values = []
        for field_name in available_fields:
            field_lower = field_name.lower()
            if hasattr(item, field_lower):
                val = getattr(item, field_lower)
            else:
                val = ""
            # Truncate long values
            val_str = str(val) if val else ""
            if len(val_str) > 14:
                val_str = val_str[:12] + ".."
            values.append(val_str)

        row = " | ".join(f"{val:<15}" for val in values)
        print(row)

    if len(inventory_items) > 20:
        print(f"... and {len(inventory_items) - 20} more items")
    print("-" * 100)
