"""
Error Handling domain step definitions.

This package contains BDD step definitions for error handling and edge case scenarios
including file system errors, network issues, and graceful degradation testing.

Step definitions are automatically discovered through the main steps/__init__.py
using pkgutil.walk_packages() dynamic loading pattern.
"""

# Import all step definition modules for automatic discovery
from . import edge_cases  # noqa: F401 - Single feature domain per YAGNI principle

# All error handling step definitions are in edge_cases.py
# following YAGNI principle for single-feature domains

__all__ = ["edge_cases"]
