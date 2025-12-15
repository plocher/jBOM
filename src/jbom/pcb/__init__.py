"""PCB integration package.

Provides:
- PCB board loading (.kicad_pcb files)
- Board model and component data structures
- Position file generation
"""
# Backward compatibility: re-export from new locations
from jbom.loaders.pcb import PCBLoader as BoardLoader, load_board

__all__ = ["BoardLoader", "load_board"]
