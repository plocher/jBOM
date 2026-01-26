# jBOM Example Inventory Files

This directory contains example inventory files that demonstrate jBOM's multi-supplier inventory capabilities.

## Multi-Supplier Inventory Pattern

jBOM is designed to support **supplier alternatives** through the use of Internal Part Numbers (IPNs). The key concept is that multiple inventory items can share the same IPN as long as they have identical electrical characteristics but different sourcing information.

### Example: Multi-Supplier Components

In `example-INVENTORY.csv`, you'll find several examples of this pattern:

```csv
IPN,Category,Value,Package,Manufacturer,MFGPN,Priority,Distributor
SWI_EDG-104,SWI,EDG-104,DIP-8,ECE,EDG104S,10,JLC
SWI_EDG-104,SWI,EDG-104,DIP-8,ECE,EDG104S,1,SPCoast
```

**Key Points:**
- **Same IPN**: Both items use `SWI_EDG-104`
- **Same Electrical Specs**: Value, Package, and core characteristics are identical
- **Different Suppliers**: JLC vs SPCoast distribution channels
- **Priority Ranking**: Lower numbers indicate higher priority (SPCoast=1, JLC=10)

### How Fabricator Filtering and Matching Works

When you use jBOM with fabricator filtering (e.g., `--fabricator JLC`), the system:

1. **Pre-filters Inventory**: Applies fabricator filters to inventory items before matching begins
2. **Component Matching**: For each KiCad component, attempts to find matching inventory items:
   - **Perfect Match**: If component has an IPN that matches inventory item(s), use those
   - **Heuristic Match**: Otherwise, use electrical/physical characteristics to find candidates
   - **Priority Selection**: When multiple items match, chooses highest priority (lowest number)
3. **Match Confidence**: Returns results only if confidence level is sufficient

The key insight is that **fabricator filtering happens before matching**, not after. This ensures that only relevant supplier alternatives are considered during the component matching process.

### Valid vs Invalid Patterns

✅ **Valid Multi-Supplier Pattern:**
```csv
IPN,Category,Value,Package,Manufacturer,MPN,Priority
RES_10K_0603,RESISTOR,10k,0603,Yageo,RC0603FR-0710KL,1
RES_10K_0603,RESISTOR,10k,0603,Vishay,CRCW060310K0FKEA,2
```

❌ **Invalid - Conflicting Electrical Specs:**
```csv
IPN,Category,Value,Package,Manufacturer,MPN,Priority
RES_10K_0603,RESISTOR,10k,0603,Yageo,RC0603FR-0710KL,1
RES_10K_0603,RESISTOR,22k,0603,Vishay,CRCW060310K0FKEA,2  # Different value!
```

## File Descriptions

- **example-INVENTORY.csv**: Comprehensive example with multi-supplier patterns
- **SPCoast-INVENTORY.csv**: Single-supplier inventory for comparison
- **JLCPCB-INVENTORY.xlsx**: JLC-specific inventory format example

## Best Practices

1. **Use consistent IPNs** as electrical specification identifiers
2. **Set appropriate priorities** to rank supplier preferences
3. **Maintain electrical characteristic consistency** within IPN groups
4. **Use fabricator filtering** to select appropriate suppliers for your build

## Important Notes

**IPN Creation**: jBOM only creates IPNs when generating a new inventory from a KiCad project (workflow B above). During BOM generation with existing inventory (workflow C), jBOM matches components to existing inventory items but does not create new IPNs.

**Matching Priority**: The system first tries exact IPN matches, then falls back to heuristic matching based on electrical characteristics. This ensures reliable component identification while supporting flexible inventory management.

This approach enables flexible supplier management while maintaining data integrity through electrical specification validation.
