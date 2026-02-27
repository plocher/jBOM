# Multi-Modal BDD Patterns

This document demonstrates the DRY approach to multi-modal testing in jBOM.

## ✅ Recommended Pattern: Shared Multi-Modal Steps

### Before (Anti-Pattern - Violates DRY):
```gherkin
Scenario Outline: Component matching
  Given the schematic contains a 10K resistor
  When I generate BOM using <method>
  Then the command succeeds

  Examples:
    | method      |
    | CLI         |
    | Python API  |
    | KiCad plugin|
```

**Problem**: Every scenario must repeat the same 3-method pattern = massive duplication

### After (DRY Pattern):
```gherkin
Scenario: Component matching
  Given the schematic contains a 10K resistor
  When I validate behavior across all usage models
  Then all usage models produce consistent results
```

**Benefit**: Write once, test across CLI, API, and plugin automatically

## Available Multi-Modal Steps

### 1. Test All Usage Models (Most Common)
```gherkin
When I validate behavior across all usage models
Then all usage models produce consistent results
```

### 2. Test Specific Operation Across All Models
```gherkin
When I validate BOM generation across all usage models
When I validate POS generation across all usage models
When I validate inventory extraction across all usage models
```

### 3. Test Specific Methods Only (When Needed)
```gherkin
When I test BOM generation using CLI, Python API
When I test POS generation using Python API, KiCad plugin
```

### 4. Individual Method Testing (Edge Cases)
```gherkin
When I generate BOM using CLI
When I generate BOM using Python API
When I generate BOM using KiCad plugin
```

## Result:
- **1 scenario** automatically becomes **3 tests** (CLI + API + plugin)
- **No duplication** in feature files
- **Easy maintenance** - change behavior once, affects all methods
- **Clear intent** - explicitly states multi-modal requirement
