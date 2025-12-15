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
)
from jbom.pcb.board_loader import load_board
from jbom.pcb.position import PositionGenerator, PlacementOptions


def find_best_pcb(search_path: Path) -> Optional[Path]:
    """Find the best PCB file in a directory or return the file itself.
    
    Args:
        search_path: Directory or .kicad_pcb file path
        
    Returns:
        Path to .kicad_pcb file, or None if not found
    """
    if search_path.is_file() and search_path.suffix == '.kicad_pcb':
        return search_path
    
    if not search_path.is_dir():
        return None
    
    # Find all PCB files in directory
    pcb_files = list(search_path.glob('*.kicad_pcb'))
    if not pcb_files:
        print(f"No .kicad_pcb file found in {search_path}", file=sys.stderr)
        return None
    
    # Separate autosave and normal files
    normal_files = [f for f in pcb_files if not f.name.startswith('_autosave-')]
    autosave_files = [f for f in pcb_files if f.name.startswith('_autosave-')]
    
    dir_name = search_path.name
    
    # Prefer normal files that match directory name
    matching_normal = [f for f in normal_files if f.stem == dir_name]
    if matching_normal:
        return matching_normal[0]
    
    # Use any normal file
    if normal_files:
        return sorted(normal_files)[0]
    
    # Fall back to autosave files with warning
    if autosave_files:
        print(f"WARNING: Only autosave PCB files found in {search_path}. Using autosave file (may be incomplete).", file=sys.stderr)
        matching_autosave = [f for f in autosave_files if f.stem == f'_autosave-{dir_name}']
        if matching_autosave:
            return matching_autosave[0]
        return sorted(autosave_files)[0]
    
    return None


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
    p.add_argument('board', help='KiCad project directory or .kicad_pcb path')
    p.add_argument('-o', '--output', help='Output CSV path (default: PROJECT_pos.csv)')
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

    fields_arg = args.fields
    if args.jlc:
        if not fields_arg:
            fields_arg = '+jlc'
        elif '+jlc' not in fields_arg.split(','):
            fields_arg = '+jlc,' + fields_arg
    fields = gen.parse_fields_argument(fields_arg) if fields_arg else gen.parse_fields_argument('+kicad_pos')
    
    # Determine output path
    if args.output:
        out = Path(args.output)
    else:
        # Default output name
        if board_path_input.is_dir():
            out = board_path_input / f"{board_path_input.name}_pos.csv"
        else:
            out = board_path.parent / f"{board_path.stem}_pos.csv"
    
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
