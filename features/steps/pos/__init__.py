"""POS generation step definitions package."""

# Import step definitions to ensure they are loaded by behave
# All POS step definitions are in component_placement.py
# following YAGNI principle for single-feature domains

from . import (
    component_placement,
)  # noqa: F401 - Single feature domain per YAGNI principle

__all__ = ["component_placement"]
