"""jBOM CLI (breaking v2): subcommands 'bom' and 'pos'.

- bom: generate BOM from schematic (existing algorithm)
- pos: generate placement/CPL from PCB
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

from jbom.jbom import (
    GenerateOptions,
    generate_bom_api,
    _parse_fields_argument,
)
from jbom.pcb.board_loader import load_board
from jbom.pcb.position import PositionGenerator, PlacementOptions


def _cmd_bom(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog='jbom bom', description='Generate BOM (CSV)')
    p.add_argument('project', help='KiCad project directory or .kicad_sch path')
    p.add_argument('-i', '--inventory', required=True, help='Inventory file (.csv/.xlsx/.xls/.numbers)')
    p.add_argument('-o', '--output', help='Output CSV path')
    p.add_argument('--outdir', help='Output directory if --output not provided')
    p.add_argument('-f', '--fields', help='Fields/presets (e.g., +jlc or Reference,Value,...)')
    p.add_argument('--jlc', action='store_true', help='Imply +jlc field preset')
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-d', '--debug', action='store_true')
    p.add_argument('--smd-only', action='store_true')
    args = p.parse_args(argv)

    opts = GenerateOptions(verbose=args.verbose, debug=args.debug, smd_only=args.smd_only, fields=None)
    result = generate_bom_api(args.project, args.inventory, options=opts)

    # Compute fields (apply --jlc implication)
    any_notes = any(((e.notes or '').strip()) for e in result['bom_entries'])
    fields_arg = args.fields
    if args.jlc:
        if not fields_arg:
            fields_arg = '+jlc'
        elif '+jlc' not in fields_arg.split(','):
            fields_arg = '+jlc,' + fields_arg
    if fields_arg:
        fields = _parse_fields_argument(fields_arg, result['available_fields'], include_verbose=args.verbose, any_notes=any_notes)
    else:
        fields = _parse_fields_argument('+standard', result['available_fields'], include_verbose=args.verbose, any_notes=any_notes)

    # Determine output path
    out = Path(args.output) if args.output else None
    if out is None:
        base = Path(args.project)
        if base.is_dir():
            name = base.name
            out = (Path(args.outdir) if args.outdir else base) / f"{name}_bom.csv"
        else:
            out = (Path(args.outdir) if args.outdir else base.parent) / f"{base.stem}_bom.csv"

    # Write via BOMGenerator (recreate matcher)
    from jbom.jbom import InventoryMatcher, BOMGenerator
    matcher = InventoryMatcher(Path(args.inventory))
    bom_gen = BOMGenerator(result['components'], matcher)
    bom_gen.write_bom_csv(result['bom_entries'], out, fields)

    return 0


def _cmd_pos(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog='jbom pos', description='Generate placement/CPL CSV')
    p.add_argument('board', help='.kicad_pcb path')
    p.add_argument('-o', '--output', required=True, help='Output CSV path')
    p.add_argument('-f', '--fields', help='Fields/presets (e.g., +jlc, +kicad_pos, Reference,X,Y,...)')
    p.add_argument('--jlc', action='store_true', help='Imply +jlc field preset')
    p.add_argument('--units', choices=['mm', 'inch'], default='mm')
    p.add_argument('--origin', choices=['board', 'aux'], default='board')
    p.add_argument('--smd-only', action='store_true', default=True)
    p.add_argument('--layer', choices=['TOP', 'BOTTOM'])
    p.add_argument('--loader', choices=['auto', 'pcbnew', 'sexp'], default='auto')
    args = p.parse_args(argv)

    board = load_board(Path(args.board), mode=args.loader)
    opts = PlacementOptions(units=args.units, origin=args.origin, smd_only=args.smd_only, layer_filter=args.layer)
    gen = PositionGenerator(board, opts)

    fields_arg = args.fields
    if args.jlc:
        if not fields_arg:
            fields_arg = '+jlc'
        elif '+jlc' not in fields_arg.split(','):
            fields_arg = '+jlc,' + fields_arg
    fields = gen.parse_fields_argument(fields_arg) if fields_arg else gen.parse_fields_argument('+kicad_pos')
    gen.write_csv(Path(args.output), fields)
    return 0


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help'):
        print('Usage: jbom {bom|pos} [options]\n'\
              '  jbom bom -i INVENTORY PROJECT_OR_SCH [options]\n'\
              '  jbom pos BOARD.kicad_pcb -o OUT.csv [options]')
        return 0
    cmd, *rest = argv
    if cmd == 'bom':
        return _cmd_bom(rest)
    if cmd == 'pos':
        return _cmd_pos(rest)
    print(f"Unknown command: {cmd}. Use 'bom' or 'pos'.", file=sys.stderr)
    return 2
