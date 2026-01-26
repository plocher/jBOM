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

### How Fabricator Filtering Works

When you use jBOM with fabricator filtering (e.g., `--fabricator JLC`), the system:

1. **Groups by IPN**: Finds all items with the same IPN
2. **Applies Filters**: Removes items that don't match fabricator criteria
3. **Selects by Priority**: Chooses the highest priority (lowest number) from remaining options

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

This approach enables flexible supplier management while maintaining data integrity through electrical specification validation.
