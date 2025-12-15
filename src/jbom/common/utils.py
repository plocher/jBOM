"""Utility helpers for file discovery and project navigation.

Provides functions to find KiCad schematic and PCB files in project directories.
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Optional

__all__ = [
    "find_best_schematic",
    "find_best_pcb",
    "is_hierarchical_schematic",
    "extract_sheet_files",
    "process_hierarchical_schematic",
]


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


def find_best_schematic(search_dir: Path) -> Optional[Path]:
    """Find the best schematic file in a directory, handling autosave files appropriately."""
    schematic_files = list(search_dir.glob('*.kicad_sch'))
    if not schematic_files:
        print(f"No .kicad_sch file found in {search_dir}")
        return None
    
    # Separate autosave and normal files
    normal_files = [f for f in schematic_files if not f.name.startswith('_autosave-')]
    autosave_files = [f for f in schematic_files if f.name.startswith('_autosave-')]
    
    dir_name = search_dir.name
    
    # First, look for hierarchical root schematics (they usually match the directory name)
    # Check both normal and autosave files for hierarchical structure
    all_candidates = []
    
    # Prefer normal files that match directory name
    matching_normal = [f for f in normal_files if f.stem == dir_name]
    if matching_normal:
        all_candidates.extend(matching_normal)
    
    # Check autosave files that match directory name
    matching_autosave = [f for f in autosave_files if f.stem == f'_autosave-{dir_name}']
    if matching_autosave:
        all_candidates.extend(matching_autosave)
    
    # Check if any candidate is hierarchical
    for candidate in all_candidates:
        if is_hierarchical_schematic(candidate):
            if candidate.name.startswith('_autosave-'):
                print(f"WARNING: Using autosave file {candidate.name} as it contains the hierarchical root (may be incomplete).")
            return candidate
    
    # No hierarchical root found matching directory name, fall back to regular selection
    if normal_files:
        # Prefer files that match the directory name, then check for hierarchical structure
        for f in sorted(normal_files):
            if is_hierarchical_schematic(f):
                return f
        
        # No hierarchical files found, return directory-matching or first file
        if matching_normal:
            return matching_normal[0]
        return sorted(normal_files)[0]
    
    elif autosave_files:
        # Only autosave files available - warn and use them
        print(f"WARNING: Only autosave files found in {search_dir}. Using autosave file (may be incomplete).")
        
        # Check for hierarchical autosave files first
        for f in sorted(autosave_files):
            if is_hierarchical_schematic(f):
                return f
        
        # No hierarchical autosave, return directory-matching or first
        if matching_autosave:
            return matching_autosave[0]
        return sorted(autosave_files)[0]
    
    return None


def is_hierarchical_schematic(schematic_path: Path) -> bool:
    """Check if a schematic file contains sheet references (hierarchical design)."""
    try:
        with open(schematic_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for sheet definitions that reference other files
            return '(sheet' in content and 'Sheetfile' in content
    except Exception:
        return False


def extract_sheet_files(schematic_path: Path) -> list[str]:
    """Extract referenced sheet file names from a hierarchical schematic."""
    sheet_files = []
    try:
        with open(schematic_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse S-expressions to find sheet file references
        import re
        # Look for (property "Sheetfile" "filename.kicad_sch") patterns
        sheet_pattern = r'\(property\s+"Sheetfile"\s+"([^"]+\.kicad_sch)"'
        matches = re.findall(sheet_pattern, content)
        sheet_files.extend(matches)
        
    except Exception as e:
        print(f"Warning: Could not parse hierarchical references from {schematic_path}: {e}")
    
    return sheet_files


def process_hierarchical_schematic(schematic_path: Path, search_dir: Path) -> list[Path]:
    """Process a schematic and return all files to be parsed (including hierarchical sheets)."""
    files_to_process = []
    
    if is_hierarchical_schematic(schematic_path):
        # Get referenced sheet files
        sheet_files = extract_sheet_files(schematic_path)
        
        if sheet_files:
            # Add the root schematic first (though it might be empty)
            files_to_process.append(schematic_path)
            
            # Add referenced sheet files if they exist
            for sheet_file in sheet_files:
                sheet_path = search_dir / sheet_file
                if sheet_path.exists():
                    files_to_process.append(sheet_path)
                else:
                    print(f"Warning: Referenced sheet file not found: {sheet_path}")
        else:
            # Hierarchical schematic but no valid sheet references found
            files_to_process.append(schematic_path)
    else:
        # Single schematic file
        files_to_process.append(schematic_path)
    
    return files_to_process
