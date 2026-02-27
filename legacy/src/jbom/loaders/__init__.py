"""File loaders for jBOM.

Loads input files from various formats:
- Schematics: KiCad .kicad_sch files
- PCBs: KiCad .kicad_pcb files
- Inventory: CSV, Excel (.xlsx, .xls), Apple Numbers files
"""

from jbom.loaders.schematic import SchematicLoader
from jbom.loaders.pcb import PCBLoader, load_board
from jbom.loaders.pcb_model import BoardModel, PcbComponent
from jbom.loaders.inventory import InventoryLoader

__all__ = [
    "SchematicLoader",
    "PCBLoader",
    "load_board",
    "BoardModel",
    "PcbComponent",
    "InventoryLoader",
]
