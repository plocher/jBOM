"""Output generators for jBOM.

Generates fabrication files:
- BOM: Bill of Materials from schematics and inventory
- POS: Component placement (CPL) from PCB layouts
"""

from jbom.generators.bom import BOMGenerator
from jbom.generators.pos import POSGenerator

__all__ = [
    "BOMGenerator",
    "POSGenerator",
]
