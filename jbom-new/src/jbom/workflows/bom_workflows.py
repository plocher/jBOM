"""BOM generation workflows that orchestrate services."""

from pathlib import Path
from typing import Optional

from jbom.services.readers.schematic_reader import SchematicReader
from jbom.services.generators.bom_generator import BOMGenerator, BOMData
from jbom.services.matchers.inventory_matcher import InventoryMatcher
from jbom.common.options import GeneratorOptions


def generate_basic_bom(
    schematic_file: Path,
    project_name: Optional[str] = None,
    options: Optional[GeneratorOptions] = None,
) -> BOMData:
    """Generate basic BOM from schematic file.

    Args:
        schematic_file: Path to .kicad_sch file
        project_name: Project name for BOM metadata
        options: Generation options

    Returns:
        BOMData with basic component information
    """
    # Use services to generate BOM
    reader = SchematicReader(options)
    generator = BOMGenerator()

    # Load components and generate BOM
    components = reader.load_components(schematic_file)
    project_name = project_name or schematic_file.stem

    return generator.generate_bom_data(components, project_name)


def generate_inventory_enhanced_bom(
    schematic_file: Path,
    inventory_file: Path,
    project_name: Optional[str] = None,
    options: Optional[GeneratorOptions] = None,
    match_strategy: str = "ipn_fuzzy",
) -> BOMData:
    """Generate BOM enhanced with inventory information.

    Args:
        schematic_file: Path to .kicad_sch file
        inventory_file: Path to inventory CSV file
        project_name: Project name for BOM metadata
        options: Generation options
        match_strategy: Inventory matching strategy

    Returns:
        BOMData enhanced with inventory information
    """
    # Use services to generate enhanced BOM
    reader = SchematicReader(options)
    generator = BOMGenerator()
    matcher = InventoryMatcher()

    # Step 1: Load components from schematic
    components = reader.load_components(schematic_file)
    project_name = project_name or schematic_file.stem

    # Step 2: Generate basic BOM
    bom_data = generator.generate_bom_data(components, project_name)

    # Step 3: Enhance with inventory data
    enhanced_bom = matcher.enhance_bom_with_inventory(
        bom_data, inventory_file, match_strategy
    )

    return enhanced_bom


def generate_filtered_bom(
    schematic_file: Path,
    project_name: Optional[str] = None,
    aggregation_strategy: str = "value_footprint",
    exclude_dnp: bool = True,
    include_only_bom: bool = True,
    options: Optional[GeneratorOptions] = None,
) -> BOMData:
    """Generate BOM with custom filtering and aggregation.

    Args:
        schematic_file: Path to .kicad_sch file
        project_name: Project name for BOM metadata
        aggregation_strategy: How to group components
        exclude_dnp: Whether to exclude DNP components
        include_only_bom: Whether to include only components marked for BOM
        options: Generation options

    Returns:
        BOMData with custom filtering applied
    """
    # Use services with custom configuration
    reader = SchematicReader(options)
    generator = BOMGenerator(aggregation_strategy)

    # Load components
    components = reader.load_components(schematic_file)
    project_name = project_name or schematic_file.stem

    # Generate BOM with custom filters
    filters = {
        "exclude_dnp": exclude_dnp,
        "include_only_bom": include_only_bom,
    }

    return generator.generate_bom_data(components, project_name, filters)
