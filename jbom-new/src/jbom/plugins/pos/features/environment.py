"""Environment configuration for POS plugin features.

This file helps behave discover step definitions in the POS plugin directory.
"""

import sys
from pathlib import Path


def before_all(context):
    """Set up POS plugin test environment."""
    # Ensure the POS plugin steps are importable
    pos_steps_dir = Path(__file__).parent / "steps"
    if pos_steps_dir not in sys.path:
        sys.path.insert(0, str(pos_steps_dir))

    # Import the POS step definitions
    try:
        import pos_steps  # noqa: F401
    except ImportError as e:
        print(f"Warning: Could not import POS step definitions: {e}")
