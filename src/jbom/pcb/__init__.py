"""PCB integration package.

Provides:
- PCB board loading (.kicad_pcb files)
- Board model and component data structures
- Position file generation
"""
from jbom.pcb.loader import BoardLoader, load_board

__all__ = ["BoardLoader", "load_board"]
