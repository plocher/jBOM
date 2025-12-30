# jBOM Inventory Search Best Practices

## Component Filtering Best Practices

### 1. DNP (Do Not Populate) Field Support

Instead of hardcoding component categories to exclude, use data-driven filtering based on component metadata:

**Preferred Approach:**
```python
# Check for DNP (Do Not Populate) field - best practice
if hasattr(item, 'dnp') and item.dnp and str(item.dnp).upper() in ['TRUE', '1', 'YES', 'DNP']:
    continue
if hasattr(item, 'exclude_from_bom') and item.exclude_from_bom and str(item.exclude_from_bom).upper() in ['TRUE', '1', 'YES']:
    continue
```

**Benefits:**
- Flexible: Components can be individually marked as DNP
- Accurate: Reflects actual BOM requirements from KiCad project
- Future-proof: Works with any component type
- Standards-compliant: Uses standard PCB industry terminology

### Component Categories

**Current searchable categories and Search Term Mapping:**
Component categories map to distributor-friendly search terms:

```python
type_keywords = {
    "RES": "resistor",
    "CAP": "capacitor",
    "IND": "inductor",
    "LED": "LED",
    "DIO": "diode",
    "IC": "IC",
    "Q": "transistor",
    "REG": "regulator",
    "CON": "connector",
    "MCU": "microcontroller",
    "RLY": "relay",
    "SWI": "switch",
}
```

**Excluded categories:**
There are some items that are not usually represented as inventory items:
- `SLK` - Silkscreen- or copper-only printing and test pads
- `BOARD` - Board outlines
- `DOC` - Documentation symbols
- `MECH` - Mechanical parts


## Integration with KiCad Workflow

### DNP Field Sources
The DNP information should ideally come from:

1. **Component Properties**: `dnp` field in schematic component
2. **BOM Exclusion**: `exclude_from_bom` field
3. **Fab Notes**: Custom fields indicating assembly exclusions

### Future Enhancements
- Support for assembly variants (different DNP sets)
- Cost analysis including DNP vs populate decisions
- Integration with pick-and-place exclusion lists

## Search Query Enhancement

### Description-First Search Strategy

**Problem**: Generic searches using only part numbers from the inventory file can return irrelevant results
- Example: "EDG-104 switch" returned AC/DC converter ICs instead of quad DIP-8 SPST switches

**Solutions**:
- Use the description field to provide targeted context
- Good descriptions are often found on data sheets

```python
# Use Description field for better search results
if hasattr(item, 'description') and item.description:
    desc = item.description.strip()
    if item.category.upper() in ['SWI', 'CON', 'RLY', 'MCU']:
        cleaned_desc = desc.replace('PTH', '').replace('SMD', '').strip()
        if len(cleaned_desc) > 10:  # Detailed description
            return cleaned_desc  # Use full description as search query
```

**Results**:
- "SPST x4 DIP Switch" → Returns actual DIP switches (TE Connectivity GDH04S04)
- "Round Button... Tactile Switch" → Returns tactile switches
- "Tag Connect 6-pin programming cable" → Returns programming connectors

### Component-Specific Search Logic

**Switches (SWI)**:
- Use Type field or Description instead of the ambiguous Value field
- Detect "SPST/DPDT" patterns, "DIP", "ON-OFF-(ON)" and "Momentary" for specific switch types
- "4 Position DIP Switch" is more specific than "DIP switch"

**Connectors (CON)**:
- Use Pitch and Pins fields to provide details: pitch:0.1", pins:2x3
- Leverage detailed Description field to give more context

**Traditional Components (RES, CAP, LED)**:
- Use good value-based descriptions ("1k resistor 0603")
- Precision/tolerance can be derived or explicit ("1k0 resistor" or "1k resistor 5%")
   - Resistors follow a "decade" pattern of values that are the same ecept for the magnitude.
   - Resistors typically are available in 20%, 10%, 5%, 2% and 1% tolerances
   - Specialty resistors are available in 0.5%, 0.1% and tighter.
- The precision of a capacitor (its tolerance) is typically indicated by a letter code that follows the capacitance value marking. A smaller tolerance percentage means higher precision.
   - The following letters are standardized codes used to indicate how much the actual capacitance value can vary from the marked value:
      * B: ±0.1% or ±0.1 pF
      * C: ±0.25% or ±0.25 pF
      * D: ±0.5% or ±0.5 pF
      * F: ±1% (High precision, common for film capacitors)
      * G: ±2% (Precision grade)
      * J: ±5% (Very common for film and ceramic capacitors)
      * K: ±10% (Common for ceramic and tantalum capacitors)
      * M: ±20% (Standard for general-purpose electrolytic capacitors)
      * Z: +80% / -20% (Wide tolerance, usually for non-critical applications)
- Unnecessarily verbose descriptions may be counterproductive

## Workflow Best Practices

### Inventory Validation and Enhancement Workflow

When distributor search doesn't find the specified manufacturer part number:

1. **Assessment**: The inventory item may not be fabrication-ready.  Important details may be missing, the item may be obsolete or otherwise unavailable.
2. **Action**: Add new line items or update the existing ones with more information from search results
3. **Improvement**: Enhance descriptions and detail fields in the inventory file
4. **Validation**: Use Product Category and descriptions from results

**Example Process**:
- Original: `SWI_EDG-104` with MPN "ECE EDG104S" → No results
- Search: "SPST x4 DIP Switch" → Finds TE Connectivity alternatives
- Decision: Add TE Connectivity GDH04S04 as new inventory line
- Update: Improve description to "4-Position SPST DIP Switch"

## Implementation Notes

These best practices are implemented in:
- `enhanced_search_validation.py` - Enhanced validation script with improved query building
- `cache_preloader.py` - Cache preloading utility
- `test_search_queries.py` - Query building validation test
- `src/jbom/cli/inventory_search_command.py` - Main CLI command

The changes maintain backward compatibility while providing:
- More accurate search results for specialized components
- Better use of inventory metadata (Description, Type fields)
- Workflow guidance for inventory enhancement
