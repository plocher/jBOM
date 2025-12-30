# Multi-Distributor Inventory Schema Proposal
## Example Transformations

**Before (LCSC-biased)**:
```csv
SWI_EDG-104,EDG-104 SPSTx4 DIP,...,C840579,ECE,EDG104S,...,JLC,100,100,0.228,$22.80
```

**After (Multi-distributor)**:
```csv
SWI_EDG-104,EDG-104 SPSTx4 DIP,...,LCSC,C840579,ECE,EDG104S,...,JLC,100,100,0.228,$22.80
```

**With Enhancement Recommendations**:
```csv
SWI_EDG-104,EDG-104 SPSTx4 DIP,...,Mouser,506-GDH04S04,TE Connectivity,GDH04S04,...,JLC,5040,5040,1.08,$5443.20
```

## Multi-Distributor Examples

### LCSC Part
```csv
CAP_0.01uF_0603,0.01uF 10% X7R 25V,...,LCSC,C1852832,YAGEO,CC0603KPX7R8BB103,...,JLC,3463,3463,0.0025,$8.66
```

### Mouser Part
```csv
CAP_0.01uF_0603,0.01uF 10% X7R 25V,...,Mouser,603-CC603KPX7R8BB103,YAGEO,CC0603KPX7R8BB103,...,Mouser,10000,10000,0.012,$120.00
```

### DigiKey Part
```csv
RES_1k_0603,1k resistor 5% 0603,...,DigiKey,311-1.00KHRCT-ND,YAGEO,RC0603FR-071KL,...,DigiKey,5000,5000,0.008,$40.00
```

### Direct/Specialty Supplier
```csv
CON_TC2030-NL,Tag Connect 6-pin,...,Direct,TC2030-NL,Tag Connect,TC2030-NL,...,Direct,10,10,8.50,$85.00
```

## Implementation Impact on jBOM

### 1. Inventory Loader Changes
**File**: `src/jbom/loaders/inventory.py`

```python
# Current
item.lcsc = row.get('LCSC', '')

# New
item.distributor = row.get('Distributor', 'LCSC')  # Default fallback
item.dpn = row.get('DPN', '')  # Distributor Part Number
```

### 2. Config File Structure Changes
**File**: `src/jbom/config/distributor_config.py`

```python
# Current - hardcoded LCSC bias
DISTRIBUTOR_CONFIGS = {
    'default': {
        'lcsc_column': 'LCSC',
        'base_url': 'https://lcsc.com/product-detail/'
    }
}

# New - flexible multi-distributor
DISTRIBUTOR_CONFIGS = {
    'LCSC': {
        'dpn_column': 'DPN',
        'base_url': 'https://lcsc.com/product-detail/{dpn}',
        'api_provider': 'LCSCProvider'
    },
    'Mouser': {
        'dpn_column': 'DPN',
        'base_url': 'https://mouser.com/ProductDetail/{dpn}',
        'api_provider': 'MouserProvider'
    },
    'DigiKey': {
        'dpn_column': 'DPN',
        'base_url': 'https://digikey.com/product-detail/en/-/{dpn}',
        'api_provider': 'DigiKeyProvider'
    },
    'Direct': {
        'dpn_column': 'DPN',
        'base_url': None,  # No standard URL pattern
        'api_provider': None
    }
}
```

### 3. BOM Generation Updates
**File**: `src/jbom/generators/bom.py`

```python
# Current - assumes LCSC
def get_purchase_url(item):
    return f"https://lcsc.com/product-detail/{item.lcsc}"

# New - distributor-aware
def get_purchase_url(item):
    config = DISTRIBUTOR_CONFIGS.get(item.distributor, {})
    url_template = config.get('base_url')
    if url_template and item.dpn:
        return url_template.format(dpn=item.dpn)
    return None
```

## Migration Strategy

### Phase 1: Backward Compatibility
- Add new columns (`Distributor`, `DPN`) alongside existing `LCSC`
- Default `Distributor="LCSC"` and `DPN=LCSC` for existing data
- Update loaders to read both schemas

### Phase 2: Data Migration
- Run inventory enhancement workflow to populate Mouser alternatives
- Migrate existing LCSC values: `LCSC → DPN`, add `Distributor="LCSC"`
- Create migration script for existing inventories

### Phase 3: Schema Finalization
- Remove deprecated `LCSC` column
- Update all documentation and examples
- Full multi-distributor support in jBOM core

## Benefits

### ✅ **Flexibility**
- Support any distributor (Mouser, DigiKey, Newark, Farnell, etc.)
- Easy to add new suppliers without schema changes
- Regional distributor preferences (US vs EU vs APAC)

### ✅ **Cost Optimization**
- Compare pricing across distributors
- Optimize for quantity breaks and shipping
- Handle distributor stock-outs gracefully

### ✅ **Supply Chain Resilience**
- Multiple sourcing options per component
- Reduce single-supplier dependency
- Better lead time management

### ✅ **Workflow Integration**
- Natural fit with distributor search enhancement
- Supports the "inventory upgrade" workflow we've built
- Enables automated distributor migration

## Compatibility Notes

### Existing Tool Integration
- **KiCad**: No impact - internal part numbers unchanged
- **LCSC/JLC**: Continues to work with `Distributor="LCSC"`
- **Assembly Houses**: `Location` field preserved and cleaned up

### API Integration
- Each distributor can have its own API provider
- Search enhancement workflow maps to appropriate distributor
- Pricing and availability checks distributor-specific

This schema change transforms jBOM from an LCSC-specific tool into a truly distributor-agnostic BOM management system, perfectly complementing the inventory enhancement workflow we've developed.
