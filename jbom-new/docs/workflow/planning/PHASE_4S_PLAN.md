# Phase 4S: Supplier Profiles

## Problem
Supplier-specific knowledge is currently either missing (DPNLink dropped in Phase 4) or conflated with fabricator configs. Fabricator profiles define *how to format output* and *which part number to prefer*. They should not own supplier-specific capabilities like URL generation, part number validation, or catalog search.

## Design
Introduce `*.supplier.yaml` profiles alongside existing `*.fab.yaml` profiles. Each supplier profile captures knowledge about one parts distributor.

### Supplier Profile Schema
```yaml
# src/jbom/config/suppliers/lcsc.supplier.yaml
name: "LCSC"
id: "lcsc"
description: "LCSC Electronics (JLCPCB parts catalog)"
website: "https://www.lcsc.com"
inventory_column: "LCSC"  # canonical column name in inventory CSV
part_number:
  pattern: "^C\\d+$"  # regex for validating part numbers
  example: "C25231"
url_template: "https://www.lcsc.com/product-detail/{pn}.html"
search_url_template: "https://www.lcsc.com/search?q={query}"
```

### Supplier Profiles to Create

**Generic** (`generic.supplier.yaml`):
- No-op supplier profile (fallback for unknown suppliers)
- `url_template`: null
- `search_url_template`: null

**LCSC** (`lcsc.supplier.yaml`):
- `inventory_column`: "LCSC"
- `part_number.pattern`: `^C\d+$`
- `url_template`: `https://www.lcsc.com/product-detail/{pn}.html`
- `search_url_template`: `https://www.lcsc.com/search?q={query}`

**Mouser** (`mouser.supplier.yaml`):
- `inventory_column`: "Mouser"
- `part_number.pattern`: `^\d{3}-.*$` (Mouser PNs typically start with 3-digit prefix)
- `url_template`: `https://www.mouser.com/ProductDetail/{pn}`
- `search_url_template`: `https://www.mouser.com/c/?q={query}`

**DigiKey** (`digikey.supplier.yaml`):
- `inventory_column`: "DigiKey"
- Direct product URLs are not reliably derivable from a bare PN without additional identifiers
- `url_template`: null (explicitly unsupported)
- `search_url_template`: `https://www.digikey.com/en/products?keywords={query}`

## Implementation

### 1. Config infrastructure

**New files**:
- `src/jbom/config/__init__.py` — make `jbom.config` a regular package
- `src/jbom/config/suppliers/` — directory for supplier YAML files (data-only; no `__init__.py`)
- `src/jbom/config/suppliers.py` — loader module (parallel to `fabricators.py`)

Note: `src/jbom/config/suppliers/__init__.py` is intentionally NOT created because it would conflict with importing `jbom.config.suppliers` (which is the loader module).

**SupplierConfig dataclass** in `suppliers.py`:
```python
@dataclass(frozen=True)
class SupplierConfig:
    id: str
    name: str
    inventory_column: str
    description: Optional[str] = None
    website: Optional[str] = None
    url_template: Optional[str] = None
    search_url_template: Optional[str] = None
    part_number_pattern: Optional[str] = None
    part_number_example: Optional[str] = None
```

**Loader functions** (mirror `fabricators.py` pattern):
- `list_suppliers() -> list[str]` — scan `*.supplier.yaml`
- `load_supplier(sid: str) -> SupplierConfig`
- `get_available_suppliers() -> list[str]`

### 2. URL generation service

**New file**: `src/jbom/services/supplier_url_resolver.py`
```python
class SupplierUrlResolver:
    def resolve_url(self, supplier_id: str, part_number: str) -> Optional[str]:
        """Generate supplier URL from part number using url_template."""

    def resolve_search_url(self, supplier_id: str, query: str) -> Optional[str]:
        """Generate supplier search URL."""
```

This replaces the dropped `DPNLink` column — URLs are derived, not stored.

### 3. Part number validation
Optional validation using `part_number.pattern`:
- `validate_part_number(supplier: SupplierConfig, pn: str) -> bool`
- Useful for inventory validation CLI (`jbom validate-inventory`)
- Not blocking for BOM generation — validation is advisory

### 4. Tests
Phase 4S scope is unit tests only:
- Unit tests for `SupplierConfig` loading and parsing
- Unit tests for URL generation (template substitution + encoding behavior)
- Unit tests for PN validation (regex matching)

## Relationship to Fabricator Profiles
Fabricator profiles and supplier profiles are **orthogonal**:
- Fab profiles reference suppliers implicitly through inventory column names (e.g., JLC's `fab_pn` synonyms include "LCSC")
- Supplier profiles define what those column names *mean* and what capabilities they enable
- A fabricator can use any combination of suppliers
- Adding a new supplier = add a `*.supplier.yaml` + optionally add column to inventory
- Adding a new fabricator = add a `*.fab.yaml` (references existing suppliers)

No code coupling between the two profile types — they connect through shared column names in inventory data.

## Integration Points (Future)
These are NOT in scope for Phase 4S but supplier profiles enable them:
- **Enriched BOM output**: Add supplier URLs as clickable links in HTML/CSV output
- **Catalog search CLI**: `jbom search "0603 100nF" --supplier lcsc` uses `search_url_template`
- **Inventory validation**: `jbom validate-inventory` checks PN formats against `part_number.pattern`
- **Multi-supplier price comparison**: Future feature using supplier APIs
- **Hierarchical config discovery**: Allow user overrides/extensions beyond factory defaults

## Reference Implementation
Follow the patterns established in `src/jbom/config/fabricators.py`:
- `_BUILTIN_DIR` pattern for locating YAML files
- `from_yaml_dict()` static method for parsing
- Frozen dataclass for config immutability
- `list_*()` / `load_*()` / `get_available_*()` function trio

## Execution Order
1. Create `suppliers.py` config loader + `SupplierConfig` dataclass
2. Create Generic, LCSC, Mouser, DigiKey supplier YAML files
3. Create `SupplierUrlResolver` service
4. Add unit tests for loader, URL resolver, PN validation

## Validation
```bash
PYTHONPATH=/Users/jplocher/Dropbox/KiCad/jBOM/jbom-new/src python -c "
from jbom.services.supplier_url_resolver import SupplierUrlResolver
r = SupplierUrlResolver()
print(r.resolve_url('lcsc','C25231'))
print(r.resolve_search_url('lcsc','0603 100nF'))
"
PYTHONPATH=/Users/jplocher/Dropbox/KiCad/jBOM/jbom-new/src python -m pytest tests/ -q --tb=short
```

## Estimated Effort
2-3 hours. Mostly config scaffolding + simple string template logic.
