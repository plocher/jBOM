"""jBOM CLI (breaking v2): subcommands 'bom' and 'pos'.

- bom: generate BOM from schematic (existing algorithm)
- pos: generate placement/CPL from PCB
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from jbom.jbom import (
    GenerateOptions,
    generate_bom_api,
    _parse_fields_argument,
    print_bom_table,
)
from jbom.pcb.board_loader import load_board
from jbom.pcb.position import PositionGenerator, PlacementOptions
from jbom.common.utils import find_best_pcb
from jbom.common.output import resolve_output_path
from jbom.cli.common import apply_jlc_flag


def _cmd_bom(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog='jbom bom', description='Generate BOM (CSV)')
    p.add_argument('project', help='KiCad project directory or .kicad_sch path')
    p.add_argument('-i', '--inventory', required=True, help='Inventory file (.csv/.xlsx/.xls/.numbers)')
    p.add_argument('-o', '--output', help='Output path (file, -, stdout for CSV, or console for formatted table)')
    p.add_argument('--outdir', help='Output directory if --output not provided')
    p.add_argument('-f', '--fields', help='Fields/presets (e.g., +jlc or Reference,Value,...)')
    p.add_argument('--jlc', action='store_true', help='Imply +jlc field preset')
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-d', '--debug', action='store_true')
    p.add_argument('--smd-only', action='store_true')
    args = p.parse_args(argv)

    opts = GenerateOptions(verbose=args.verbose, debug=args.debug, smd_only=args.smd_only, fields=None)
    result = generate_bom_api(args.project, args.inventory, options=opts)

    # Compute fields (apply --jlc implication using shared utility)
    any_notes = any(((e.notes or '').strip()) for e in result['bom_entries'])
    fields_arg = apply_jlc_flag(args.fields, args.jlc)
    if fields_arg:
        fields = _parse_fields_argument(fields_arg, result['available_fields'], include_verbose=args.verbose, any_notes=any_notes)
    else:
        fields = _parse_fields_argument('+standard', result['available_fields'], include_verbose=args.verbose, any_notes=any_notes)

    # Check output mode: CSV to stdout vs formatted console table
    output_str = args.output.lower() if args.output else ''
    csv_to_stdout = output_str in ('-', 'stdout')
    formatted_console = output_str == 'console'
    
    if formatted_console:
        # Formatted table output to console (human-readable)
        print_bom_table(result['bom_entries'], verbose=args.verbose, include_mfg=False)
    elif csv_to_stdout:
        # CSV output to stdout (pipeline-friendly)
        from jbom.jbom import InventoryMatcher, BOMGenerator
        matcher = InventoryMatcher(Path(args.inventory))
        bom_gen = BOMGenerator(result['components'], matcher)
        bom_gen.write_bom_csv(result['bom_entries'], Path('-'), fields)
    else:
        # Determine output path using shared utility
        out = resolve_output_path(
            Path(args.project),
            args.output,
            args.outdir,
            '_bom.csv'
        )
        
        # Write via BOMGenerator (recreate matcher)
        from jbom.jbom import InventoryMatcher, BOMGenerator
        matcher = InventoryMatcher(Path(args.inventory))
        bom_gen = BOMGenerator(result['components'], matcher)
        bom_gen.write_bom_csv(result['bom_entries'], out, fields)

    return 0


def _cmd_pos(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog='jbom pos', description='Generate placement/CPL CSV')
    p.add_argument('board', help='KiCad project directory or .kicad_pcb path')
    p.add_argument('-o', '--output', help='Output path (file, -, stdout, or console for CSV to stdout)')
    p.add_argument('-f', '--fields', help='Fields/presets (e.g., +jlc, +kicad_pos, Reference,X,Y,...)')
    p.add_argument('--jlc', action='store_true', help='Imply +jlc field preset')
    p.add_argument('--units', choices=['mm', 'inch'], default='mm')
    p.add_argument('--origin', choices=['board', 'aux'], default='board')
    p.add_argument('--smd-only', action='store_true', default=True)
    p.add_argument('--layer', choices=['TOP', 'BOTTOM'])
    p.add_argument('--loader', choices=['auto', 'pcbnew', 'sexp'], default='auto')
    args = p.parse_args(argv)

    # Find PCB file (auto-detect if directory)
    board_path_input = Path(args.board)
    board_path = find_best_pcb(board_path_input)
    if not board_path:
        print(f"Error: Could not find PCB file in {board_path_input}", file=sys.stderr)
        return 1
    
    board = load_board(board_path, mode=args.loader)
    opts = PlacementOptions(units=args.units, origin=args.origin, smd_only=args.smd_only, layer_filter=args.layer)
    gen = PositionGenerator(board, opts)

    # Apply --jlc flag using shared utility
    fields_arg = apply_jlc_flag(args.fields, args.jlc)
    fields = gen.parse_fields_argument(fields_arg) if fields_arg else gen.parse_fields_argument('+kicad_pos')
    
    # Check output mode: CSV to stdout (pipeline-friendly) or file
    output_str = args.output.lower() if args.output else ''
    csv_to_stdout = output_str in ('-', 'stdout', 'console')
    
    if csv_to_stdout:
        # CSV output to stdout (pipeline-friendly)
        gen.write_csv(Path('-'), fields)
    else:
        # Determine output path using shared utility
        out = resolve_output_path(
            board_path_input,
            args.output,
            None,  # pos command doesn't have --outdir
            '_pos.csv'
        )
        gen.write_csv(out, fields)
    
    return 0


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help'):
        print('Usage: jbom {bom|pos} [options]\n'\
              '  jbom bom PROJECT -i INVENTORY [options]\n'\
              '  jbom pos PROJECT [options]')
        return 0
    cmd, *rest = argv
    if cmd == 'bom':
        return _cmd_bom(rest)
    if cmd == 'pos':
        return _cmd_pos(rest)
    print(f"Unknown command: {cmd}. Use 'bom' or 'pos'.", file=sys.stderr)
    return 2
