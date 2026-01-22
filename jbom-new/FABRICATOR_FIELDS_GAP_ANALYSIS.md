# Fabricator Fields Functionality Gap Analysis

## Executive Summary

The jBOM-new fabricator support is **incomplete** compared to the mature legacy system. While the basic fabricator configurations have been migrated (Issues #22-#31), the critical **fields system** that controls output formatting, column mapping, and field presets is **entirely missing** from jBOM-new.

## Current State: What's Missing

### 1. **CLI Fields Arguments**
**Status: ❌ MISSING**

- **Legacy has**: `-f FIELDS, --fields FIELDS` argument with rich syntax support
- **jBOM-new has**: No `--fields` argument at all
- **Impact**: Users cannot customize BOM/POS output columns

**Legacy Example:**
```bash
jbom bom project/ -f +jlc,Tolerance          # JLC preset + custom field
jbom bom project/ -f Reference,Value,LCSC    # Custom field list
jbom bom project/ -f +standard,I:Voltage     # Standard preset + inventory field
```

**jBOM-new Reality:**
```bash
jbom bom project/ --fabricator jlc           # Only sets fabricator, no field control
# No way to customize output columns at all
```

### 2. **Field Preset System**
**Status: ❌ MISSING**

- **Legacy has**: Rich preset system with `+preset` syntax (`+standard`, `+jlc`, `+minimal`, `+all`)
- **jBOM-new has**: Fabricator configs contain `presets` section but **no code to use them**
- **Impact**: Fabricator presets are configured but non-functional

**Config vs. Implementation Gap:**
```yaml
# jlc.fab.yaml - Config exists but unused
presets:
  default:
    description: "JLC BOM format"
    fields: ["reference", "quantity", "value", "package", "lcsc", "smd"]
```
```python
# jbom-new CLI - No code to process presets
# fabricator = args.fabricator  # ✅ Sets fabricator
# No field preset application    # ❌ Missing entirely
```

### 3. **Column Mapping & Output Formatting**
**Status: ❌ MISSING**

- **Legacy has**: Fabricator-specific column headers and field mappings
- **jBOM-new has**: Column mappings in config but **no output formatting code**
- **Impact**: All fabricators produce identical generic output

**Expected vs. Actual Behavior:**

| Command | Legacy Output Headers | jBOM-new Output Headers |
|---------|---------------------|------------------------|
| `--fabricator jlc` | `Designator,Quantity,Value,Comment,Footprint,LCSC,Surface Mount` | `References,Value,Footprint,Quantity` |
| `--fabricator generic` | `Reference,Quantity,Description,Value,Package,Footprint,Manufacturer,Part Number` | `References,Value,Footprint,Quantity` |

### 4. **Field Parsing & Validation**
**Status: ❌ MISSING**

- **Legacy has**: Sophisticated field argument parsing with presets, custom fields, mixed syntax
- **jBOM-new has**: No field argument parsing at all
- **Impact**: No field customization, validation, or error handling

**Missing Capabilities:**
- Field normalization (`Value` → `value`, `Match Quality` → `match_quality`)
- Preset expansion (`+jlc` → `["reference", "quantity", "value", "package", "lcsc", "smd"]`)
- Field validation against available fields
- Mixed syntax support (`+standard,CustomField,I:Voltage`)

### 5. **Inventory Field Integration**
**Status: ❌ MISSING**

- **Legacy has**: `I:` prefix for inventory fields, `C:` prefix for component fields
- **jBOM-new has**: No field prefixing or inventory field system
- **Impact**: Cannot specify inventory-sourced fields in output

**Missing Examples:**
- `I:Voltage` - Show voltage from inventory data
- `I:Tolerance` - Show tolerance from inventory
- `I:Package` - Use inventory package vs. component package
- `C:Footprint` - Explicitly use component footprint

## Architecture Gap

### Legacy Architecture (Complete)
```
CLI Args: -f +jlc,I:Voltage
    ↓
Field Parser: parse_fields_argument()
    ↓
Preset Registry: expand +jlc → [fields]
    ↓
Fabricator Config: bom_columns mapping
    ↓
Output Generator: apply column headers
    ↓
CSV/Console: fabricator-specific format
```

### jBOM-new Architecture (Incomplete)
```
CLI Args: --fabricator jlc  (no -f option)
    ↓
Fabricator Loader: load config ✅
    ↓
[MISSING: Field argument parsing]
    ↓
[MISSING: Preset expansion]
    ↓
[MISSING: Column mapping application]
    ↓
Hard-coded Output: generic format only
```

## Functional Impact Analysis

### For Users
1. **No Output Customization**: Cannot control which fields appear in BOM/POS
2. **No Fabricator-Specific Formats**: JLC output looks identical to Generic
3. **No Field Presets**: Cannot use convenient `+jlc`, `+minimal` shortcuts
4. **No Inventory Field Control**: Cannot include/exclude specific inventory data
5. **Breaking Change**: Existing workflows using `-f` will fail

### For Developers
1. **Incomplete Migration**: Core functionality still missing after config migration
2. **Test Gaps**: BDD tests for fabricator formats cannot validate actual differences
3. **Feature Regression**: jBOM-new has significantly less capability than legacy

## Implementation Requirements

### Phase 1: Core Field System
1. **Add `-f/--fields` CLI argument** to BOM and POS commands
2. **Implement field argument parser** with preset and custom field support
3. **Create preset registry** that loads from fabricator configs
4. **Add field validation** against available fields from components/inventory

### Phase 2: Output Integration
1. **Implement column mapping** using fabricator `bom_columns`/`pos_columns`
2. **Update output functions** to apply fabricator-specific headers
3. **Add inventory field prefixing** (`I:`, `C:` support)
4. **Integrate with existing BOMData/POSData structures**

### Phase 3: Feature Completeness
1. **Add field listing** (`--list-fields` functionality)
2. **Support mixed syntax** (`+preset,custom,I:field`)
3. **Add verbose/debug** field options
4. **Comprehensive error handling** for unknown fields/presets

## Testing Strategy

### Unit Tests
- Field argument parsing edge cases
- Preset expansion logic
- Column mapping application
- Field validation

### Integration Tests
- Fabricator-specific output format verification
- Field preset functionality across fabricators
- Inventory field integration

### BDD Tests
- Update existing fabricator tests to validate format differences
- Add field customization scenarios
- Test mixed field/preset syntax

## Success Criteria

### User Experience
✅ `jbom bom project/ -f +jlc` produces JLCPCB-formatted output
✅ `jbom bom project/ -f Reference,Value,LCSC` shows only specified fields
✅ `jbom bom project/ --fabricator jlc -f +standard` combines fabricator + preset
✅ Different fabricators produce visibly different output formats

### Technical Implementation
✅ Field argument parser handles all legacy syntax patterns
✅ Preset registry dynamically loads from fabricator configs
✅ Column mapping produces fabricator-specific headers
✅ Inventory fields integrate seamlessly with component data

## Risk Assessment

### High Priority Issues
- **User Workflow Disruption**: Missing `-f` breaks existing automation
- **Fabricator Support Claims**: Documentation implies functionality that doesn't exist
- **Migration Incompleteness**: Core feature gap makes jBOM-new unsuitable for production

### Development Complexity
- **Medium**: Field parsing logic is well-established in legacy
- **Low**: Fabricator configs already contain needed mapping data
- **Medium**: Output integration requires careful BOMData/POSData updates

## Recommendation

**Create Issue:** "Implement fabricator field system and output customization"

**Priority:** High - This is core functionality gap that makes fabricator support incomplete

**Scope:** Medium-Large feature addition spanning CLI, services, and output formatting

**Effort:** ~2-3 weeks full implementation with comprehensive testing
