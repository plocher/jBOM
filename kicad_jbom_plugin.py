#!/usr/bin/env python3
"""
KiCad BOM plugin wrapper for jBOM.

Usage in KiCad (Eeschema -> Tools -> Generate BOM):
  Command: python3 /absolute/path/to/kicad_jbom_plugin.py %I -i /path/to/INVENTORY.xlsx -o %O [-v] [-d] [-f "Reference,Value,LCSC"]

Notes:
- %I is provided by KiCad (input schematic path)
- %O is the destination BOM file path chosen in KiCad
- This wrapper uses the jbom library API and writes a CSV file.
"""
import sys
import argparse
from pathlib import Path

# Local import
import jbom
from jbom import GenerateOptions, BOMGenerator, InventoryMatcher


def main():
    p = argparse.ArgumentParser(description="KiCad wrapper for jBOM")
    p.add_argument('schematic', help='KiCad schematic file path (%I) or project dir')
    p.add_argument('-i', '--inventory', required=True, help='Inventory file (.csv/.xlsx/.xls/.numbers)')
    p.add_argument('-o', '--output', required=True, help='Output CSV path (%O)')
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-d', '--debug', action='store_true')
    p.add_argument('-f', '--fields', help='Comma-separated custom fields')
    args = p.parse_args()

    fields = [f.strip() for f in args.fields.split(',')] if args.fields else None

    opts = GenerateOptions(
        verbose=args.verbose,
        debug=args.debug,
        smd_only=False,
        fields=fields,
    )

    # Run library API (no printing)
    result = jbom.generate_bom_api(args.schematic, args.inventory, options=opts)

    # Compute field list (mirror jbom default logic)
    any_notes = any((e.notes or '').strip() for e in result['bom_entries'])
    out_fields = fields if fields else [
        'Reference', 'Quantity', 'Description', 'Value', 'Footprint', 'LCSC',
        'Datasheet', 'SMD'
    ]
    if not fields:
        if args.verbose:
            out_fields.append('Match_Quality')
        if any_notes:
            out_fields.append('Notes')
        if args.verbose:
            out_fields.append('Priority')

    # Write CSV
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Recreate matcher for write_bom_csv field resolution
    matcher = InventoryMatcher(Path(args.inventory))
    bom_gen = BOMGenerator(result['components'], matcher)
    bom_gen.write_bom_csv(result['bom_entries'], out_path, out_fields)

    return 0


if __name__ == '__main__':
    sys.exit(main())