"""Output path resolution utilities.

Provides common logic for determining output file paths from CLI arguments.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

__all__ = [
    "resolve_output_path",
]


def resolve_output_path(
    input_path: Path,
    output_arg: Optional[str],
    outdir_arg: Optional[str],
    suffix: str,
) -> Path:
    """Resolve output path from CLI arguments.
    
    Handles various input scenarios:
    - Explicit output path: use it directly
    - Directory input + outdir: use outdir with generated name
    - Directory input: generate name in input directory
    - File input + outdir: use outdir with generated name
    - File input: generate name in parent directory
    
    Args:
        input_path: Input file or directory path
        output_arg: Explicit output path from CLI (or None)
        outdir_arg: Output directory from CLI (or None)
        suffix: File suffix to append (e.g., '_bom.csv', '_pos.csv')
        
    Returns:
        Resolved output Path
        
    Examples:
        >>> resolve_output_path(Path('project/'), None, None, '_bom.csv')
        Path('project/project_bom.csv')
        
        >>> resolve_output_path(Path('proj.kicad_sch'), None, 'out/', '_bom.csv')
        Path('out/proj_bom.csv')
        
        >>> resolve_output_path(Path('any'), 'custom.csv', None, '_bom.csv')
        Path('custom.csv')
    """
    # Explicit output path takes precedence
    if output_arg:
        return Path(output_arg)
    
    # Determine output directory and base name
    if input_path.is_dir():
        # Input is a directory: use directory name as base
        base_name = input_path.name
        out_dir = Path(outdir_arg) if outdir_arg else input_path
    else:
        # Input is a file: use file stem as base
        base_name = input_path.stem
        out_dir = Path(outdir_arg) if outdir_arg else input_path.parent
    
    # Generate output filename
    return out_dir / f"{base_name}{suffix}"
