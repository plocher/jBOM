"""
Confidence Test: Project Part Search
Demonstrates loading a real KiCad project and searching Mouser for each unique component.

Usage:
    export MOUSER_API_KEY="your_key"
    python examples/search_project_parts.py /path/to/project
"""
import sys
import os
import time
from pathlib import Path
from collections import defaultdict

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jbom.loaders.schematic import SchematicLoader  # noqa: E402
from jbom.search.mouser import MouserProvider  # noqa: E402
from jbom.search.filter import SearchFilter  # noqa: E402
from jbom.processors.component_types import get_component_type  # noqa: E402
from jbom.common.constants import ComponentType  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/search_project_parts.py <project_path> [api_key]")
        sys.exit(1)

    project_path = Path(sys.argv[1])
    api_key = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("MOUSER_API_KEY")

    if not api_key:
        print("Error: Mouser API Key required.")
        sys.exit(1)

    # 1. Load Components
    print(f"Loading project: {project_path}")
    # Find schematic file
    sch_file = next(project_path.glob("*.kicad_sch"), None)
    if not sch_file:
        print("No .kicad_sch file found.")
        sys.exit(1)

    loader = SchematicLoader(sch_file)
    components = loader.parse()
    print(f"Found {len(components)} components.")

    # 2. Group by Value/Footprint (Unique Parts)
    grouped = defaultdict(list)
    for comp in components:
        if not comp.in_bom:
            continue
        key = (comp.value, comp.footprint, comp.lib_id)
        grouped[key].append(comp)

    print(f"Unique parts to search: {len(grouped)}")
    print("-" * 60)

    # 3. Initialize Provider
    provider = MouserProvider(api_key=api_key)

    # 4. Search Loop
    start_time = time.time()

    for i, ((value, footprint, lib_id), comps) in enumerate(grouped.items()):
        refs = ", ".join(c.reference for c in comps[:3])
        if len(comps) > 3:
            refs += f" (+{len(comps)-3} more)"

        print(f"\n[{i+1}/{len(grouped)}] {refs}")
        print(f"  Spec: {value} | {footprint}")

        # Construct Query
        # Heuristic: Value + Package + Type Keyword
        comp_type = get_component_type(lib_id, footprint)
        type_keyword = ""
        if comp_type == ComponentType.RESISTOR:
            type_keyword = "resistor"
        elif comp_type == ComponentType.CAPACITOR:
            type_keyword = "capacitor"
        elif comp_type == ComponentType.INDUCTOR:
            type_keyword = "inductor"
        elif comp_type == ComponentType.LED:
            type_keyword = "LED"

        # Extract package from footprint (simple heuristic)
        pkg = ""
        if "0603" in footprint:
            pkg = "0603"
        elif "0805" in footprint:
            pkg = "0805"
        elif "0402" in footprint:
            pkg = "0402"
        elif "1206" in footprint:
            pkg = "1206"
        elif "SOT-23" in footprint:
            pkg = "SOT-23"
        elif "SOIC-8" in footprint:
            pkg = "SOIC-8"

        # Normalize Value (Unicode to ASCII)
        value = value.replace("Ω", "Ohm").replace("µ", "u").replace("uF", "uF")
        if not value or value.lower() in ("uf", "pf", "nf", "ohm", "kohm"):
            # Skip malformed values (e.g. just unit)
            print(f"  Skipping malformed value: {value}")
            continue

        query = f"{value} {type_keyword} {pkg}".strip()
        print(f'  Query: "{query}"')

        try:
            results = provider.search(query, limit=5)

            # Apply Parametric Filtering
            results = SearchFilter.filter_by_query(results, query)

            if not results:
                print("  -> No matches found.")
            else:
                print(f"  -> Found {len(results)} candidates:")
                for r in results:
                    print(
                        f"     * {r.manufacturer} {r.mpn} ({r.stock_quantity} in stock) ${r.price}"
                    )

        except Exception as e:
            print(f"  -> Error: {e}")

        # Rate Limit Sleep
        time.sleep(1.0)

    duration = time.time() - start_time
    print("-" * 60)
    print(f"Completed in {duration:.2f} seconds.")


if __name__ == "__main__":
    main()
