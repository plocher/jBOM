"""Inventory management step definitions package."""

# Import step definitions to ensure they are loaded by behave
from . import shared  # noqa: F401 - Domain-specific shared steps per Axiom #15
from . import project_extraction  # noqa: F401
from . import search_enhancement  # noqa: F401
