"""
BDD step definitions package for jBOM.

This module imports all step definitions from subdirectories using
explicit imports to ensure behave can find them.
"""

# Import all step definitions explicitly using * imports
# This is the recommended approach for behave with subdirectories

# Import shared step definitions
from .shared import *  # noqa: F403,F401

# Import BOM domain step definitions
from .bom.component_matching import *  # noqa: F403,F401
from .bom.multi_format_support import *  # noqa: F403,F401

# Import error handling domain step definitions
from .error_handling.edge_cases import *  # noqa: F403,F401
