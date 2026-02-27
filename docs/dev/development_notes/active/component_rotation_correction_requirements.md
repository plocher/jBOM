# Fabricator-Specific Component Rotation Corrections - Implementation TODO

## Overview

This document captures the requirements and research for implementing fabricator-specific component rotation corrections in jBOM, addressing the complex real-world challenges of pick-and-place manufacturing coordination.

## Problem Statement

Different PCB fabricators use different rotation standards for their pick-and-place equipment, creating a complex translation problem between KiCad's IPC-7352 standard orientations and fabricator-specific requirements.

### Technical Complexity

1. **KiCad Standard**: Follows IPC-7352 (Pin 1 in top-left, 0 degrees reference)
2. **JLCPCB "Reel Zero"**: Rotation based on tape/feeder orientation, not IPC standard
3. **Per-Part Variations**: Rotation complexity varies by component type:
   - **Passive Components (R, C)**: Generally consistent per footprint
   - **ICs**: Complex variations based on:
     * Packaging format (SOIC vs DIP vs QFN vs BGA)
     * Supplier tape orientation differences
     * Through-hole vs surface-mount versions
     * Pin 1 indicator location variations
   - **Connectors**: Highly variable based on keying and orientation
   - **Specialty Components**: Case-by-case analysis required

## Existing Solutions Research

### JLCKicadTools Project
- **Repository**: https://github.com/matthewlai/JLCKicadTools/tree/master/jlc_kicad_tools
- **Approach**: Maintains CSV database of JLCPCB part-specific rotation corrections
- **Value**: Demonstrates real-world solution to per-part rotation lookup
- **Learning**: Shows complexity of maintaining part-specific rotation database

### Key Insights from JLCKicadTools
- Cannot use mathematical offset approach (KiCad angle + constant)
- Requires extensive part-specific database maintenance
- Must account for packaging format variations, not electrical specification differences
- EIA-481 standard provides consistency within same package type (SOIC-14, MSOP-10, etc.)
- Database needs regular updates as JLCPCB changes suppliers/packaging
- Rotation differences are based on physical package geometry, not part grade/tolerance

## Implementation Requirements

### 1. Fabricator Configuration Enhancement

Extend `*.fab.yaml` files to support rotation correction strategies:

```yaml
# Example enhanced fabricator configuration
rotation_correction:
  strategy: "per_part_lookup"  # or "mathematical_offset" or "none"

  # For per-part lookup strategy
  lookup_database:
    source: "csv_file"
    file_path: "config/fabricators/jlc_rotations.csv"
    key_fields: ["MPN", "DPN", "Footprint"]
    rotation_field: "Correction_Angle"

  # For mathematical offset strategy
  mathematical_offset:
    base_offset: 0
    per_footprint_offsets:
      "QFN-32": 90
      "BGA-144": 180

  # Fallback behavior
  unknown_part_behavior: "warn_and_use_kicad_rotation"
```

### 2. Rotation Database Management

#### Database Schema
```csv
MPN,DPN,Footprint,Correction_Angle,Package_Type,Last_Updated,Source
RC0603FR-0710K,C25804,R_0603_1608,0,Reel,2024-12-01,JLCPCB_Datasheet
CC0603KRX7R9BB,C14663,C_0603_1608,0,Reel,2024-12-01,JLCPCB_Datasheet
LM324DR,C7950,SOIC-14_3.9x8.7,0,Reel,2024-12-01,JLCPCB_Datasheet
LM324IPWR,C7951,MSOP-10_3x3,180,Reel,2024-12-01,JLCPCB_Datasheet
ATMega328P-PU,C14877,DIP-32_15.24x39,90,Tray,2024-12-01,JLCPCB_Datasheet
ATMega328PB-AU,C14878,QFN-32_5x5,270,Reel,2024-12-01,JLCPCB_Datasheet
```

#### Database Sources
1. **JLCKicadTools CSV**: Import existing community database
2. **Fabricator APIs**: Direct integration where available
3. **Community Contributions**: Crowdsourced corrections
4. **Manual Entry**: For custom/specialty parts

### 3. Code Architecture

#### New Classes/Modules
```python
# rotation_corrector.py
class RotationCorrector:
    def __init__(self, fabricator_config):
        self.strategy = fabricator_config.rotation_correction.strategy
        self.lookup_db = self.load_lookup_database()

    def correct_rotation(self, component, kicad_rotation):
        if self.strategy == "per_part_lookup":
            return self.lookup_rotation_correction(component)
        elif self.strategy == "mathematical_offset":
            return self.apply_mathematical_correction(component, kicad_rotation)
        else:
            return kicad_rotation

    def lookup_rotation_correction(self, component):
        # Search database by MPN, DPN, Footprint
        # Handle missing entries with fallback behavior
        pass
```

### 4. Integration Points

#### POS Generation Pipeline
1. **Component Extraction**: Get components from PCB with KiCad rotations
2. **Inventory Matching**: Link components to MPN/DPN from inventory
3. **Rotation Correction**: Apply fabricator-specific corrections
4. **POS Output**: Generate corrected placement file

#### BOM Integration
- Rotation corrections must coordinate with BOM part selection
- Same component in BOM and POS must use same MPN/DPN
- Inventory changes may affect rotation corrections

### 5. User Experience

#### Configuration
- Fabricator configs include rotation strategy selection
- Database management commands for updates/validation
- Warning system for missing rotation data

#### Workflow
1. User generates BOM with specific fabricator (e.g., --jlc)
2. System matches components to inventory parts (MPN/DPN)
3. POS generation uses same fabricator config for rotation corrections
4. Output includes rotation correction audit trail

## Testing Requirements

### BDD Scenarios (Already Implemented)
- ✅ Cardinal rotation testing (0, 90, 180, 270 degrees)
- ✅ Fabricator-specific rotation corrections (JLCPCB vs PCBWay)
- ✅ Per-part complexity with same footprint, different rotations

### Additional Testing Needed
- Database loading and validation
- Missing part handling and fallback behavior
- Rotation correction audit logging
- Performance with large part databases
- Integration with inventory matching pipeline

## Implementation Phases

### Phase 1: Architecture Foundation
- [ ] Design rotation correction interface
- [ ] Implement rotation corrector classes
- [ ] Add fabricator config schema extensions
- [ ] Create database loading infrastructure

### Phase 2: Database Integration
- [ ] Import JLCKicadTools CSV database
- [ ] Implement per-part lookup functionality
- [ ] Add database validation and error handling
- [ ] Create database update/maintenance tools

### Phase 3: POS Integration
- [ ] Integrate rotation correction into POS generation pipeline
- [ ] Coordinate with BOM part selection for MPN/DPN consistency
- [ ] Add rotation correction audit trail to output
- [ ] Implement user-facing configuration options

### Phase 4: Additional Fabricators
- [ ] Research PCBWay rotation requirements
- [ ] Implement mathematical offset strategy
- [ ] Add Seeed Studio support
- [ ] Generic fabricator rotation configuration

## References

### Technical Standards
- IPC-7352: Land Pattern Standard
- IPC-2581: Generic Requirements for Printed Board Assembly Products Manufacturing Description Data

### External Resources
- [JLCKicadTools](https://github.com/matthewlai/JLCKicadTools/tree/master/jlc_kicad_tools): Community rotation database
- JLCPCB Component Library: Official part specifications
- KiCad PCB Format Documentation: Rotation representation

### Related Issues
- Component orientation standardization
- Pick-and-place equipment coordination
- Manufacturing file generation accuracy
- Fabricator-specific workflow optimization

## Success Criteria

1. **Accurate Rotations**: Generated POS files have correct rotations for target fabricator
2. **Database Integration**: Seamless import/update of rotation correction databases
3. **User Experience**: Simple fabricator selection automatically applies correct rotations
4. **Maintainability**: Database updates don't require code changes
5. **Performance**: Large part databases don't significantly impact generation speed
6. **Auditability**: Clear tracking of which corrections were applied and why

---

*This TODO document captures the full scope of fabricator-specific rotation correction implementation, preserving critical domain knowledge and implementation requirements for future development.*
