"""
BDD step definitions package for jBOM.

Behave will automatically discover step definitions in .py files in this directory.
The subdirectories contain organized step files that behave will discover.

Domains:
- shared.py: Cross-domain step definitions
- annotate/: Back-annotation step definitions
- bom/: Bill of Materials step definitions
- error_handling/: Error handling step definitions
- inventory/: Inventory management step definitions
- pos/: Pick-and-place step definitions
- search/: Part search step definitions

Note: This __init__.py file is kept empty to avoid import issues with behave.
Behave will discover all .py files in subdirectories automatically.
"""
