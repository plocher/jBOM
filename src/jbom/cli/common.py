"""Common CLI utilities shared between subcommands.

Provides shared logic for argument processing and command execution.
"""
from __future__ import annotations
from typing import Optional

__all__ = [
    "apply_jlc_flag",
]


def apply_jlc_flag(fields_arg: Optional[str], jlc_flag: bool) -> Optional[str]:
    """Apply --jlc flag to fields argument.
    
    The --jlc flag implies the +jlc preset. This function handles the logic
    of prepending +jlc to the fields argument when the flag is set.
    
    Args:
        fields_arg: Original fields argument (or None)
        jlc_flag: Whether --jlc flag was set
        
    Returns:
        Modified fields argument with +jlc prepended if needed
        
    Examples:
        >>> apply_jlc_flag(None, True)
        '+jlc'
        
        >>> apply_jlc_flag('Reference,Value', True)
        '+jlc,Reference,Value'
        
        >>> apply_jlc_flag('+jlc,Custom', True)
        '+jlc,Custom'
        
        >>> apply_jlc_flag('Reference,Value', False)
        'Reference,Value'
    """
    if not jlc_flag:
        return fields_arg
    
    # If no fields specified, just use +jlc
    if not fields_arg:
        return '+jlc'
    
    # If +jlc already in the argument, return as-is
    if '+jlc' in fields_arg.split(','):
        return fields_arg
    
    # Prepend +jlc to existing fields
    return f'+jlc,{fields_arg}'
