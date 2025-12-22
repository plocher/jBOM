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

### 2. Expanded Searchable Component Categories

**Current searchable categories:**
- `RES` - Resistors
- `CAP` - Capacitors
- `IND` - Inductors
- `LED` - LEDs
- `DIO` - Diodes
- `IC` - Integrated Circuits
- `Q` - Transistors
- `REG` - Regulators
- `CON` - Connectors *(new)*
- `MCU` - Microcontrollers *(new)*
- `RLY` - Relays *(new)*
- `SWI` - Switches *(new)*

**Excluded categories:**
- `SLK` - Silkscreen (rarely has distributors)
- `BOARD` - Board outlines
- `DOC` - Documentation symbols
- `MECH` - Mechanical parts

### 3. Search Term Mapping

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

### 4. Description-First Search Strategy

**Problem**: Generic searches using internal part numbers return irrelevant results
- Example: "EDG-104 switch" returned AC/DC converter ICs instead of switches

**Solution**: Use the Description field for specialized components
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

### 5. Component-Specific Search Logic

**Switches (SWI)**:
- Use Type field or Description instead of cryptic Value field
- Detect "DIP" and "Momentary" for specific switch types
- "4 Position DIP Switch" is more specific than "DIP switch"

**Connectors (CON)**:
- Leverage detailed Description field for specialized connectors
- Tag-Connect, programming headers need descriptive searches

**Traditional Components (RES, CAP, LED)**:
- Continue using value-based approach ("1k resistor 0603")
- Description often too verbose for simple components

## Workflow Best Practices

### 6. Inventory Validation and Enhancement Workflow

When distributor search doesn't find the specified MPN:

1. **Assessment**: The inventory item may not be fabrication-ready
2. **Action**: Add new line items from search results to inventory
3. **Improvement**: Enhance descriptions in inventory file
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
