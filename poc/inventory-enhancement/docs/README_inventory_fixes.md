# Inventory Unicode Normalization Fix Guide

This guide shows how to apply Unicode normalization fixes to your Numbers inventory file while preserving formulas, formatting, and table structure.

## Quick Start

### Numbers Files (Preserves Formulas & Formatting)
```bash
# 1. Analyze what fixes are needed (safe, no changes)
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py poc/inventory-enhancement/examples/test-search-INVENTORY.numbers --dry-run

# 2. Apply fixes to create a new fixed file
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py poc/inventory-enhancement/examples/test-search-INVENTORY.numbers --output poc/inventory-enhancement/examples/test-search-INVENTORY-fixed.numbers --apply

# 3. Apply fixes in-place (modifies original, creates timestamped backup)
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py poc/inventory-enhancement/examples/test-search-INVENTORY.numbers --apply
```

### Excel Files (Preserves Formulas & Formatting)
```bash
# Analyze Excel inventory
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py inventory.xlsx --dry-run

# Fix Excel file with backup
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py inventory.xlsx --apply

# Create new fixed Excel file
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py inventory.xlsx --output inventory-fixed.xlsx --apply
```

### CSV Files (Text Format Only)
```bash
# Analyze CSV inventory
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py inventory.csv --dry-run

# Fix CSV with automatic backup
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py inventory.csv --apply
```

## What Gets Fixed

The script automatically fixes Unicode symbols that cause distributor API failures:

### Resistor Values (21 items affected)
- `200Ω` → `200`
- `220Ω` → `220`
- `1kΩ` → `1k`
- `2.2kΩ` → `2.2k`
- `10kΩ` → `10k`
- `100kΩ` → `100k`
- `1MΩ` → `1M`
- etc.

### Capacitor Values (if present)
- `0.1µF` → `0.1uF`
- `1µF` → `1uF`
- etc.

## Features

### ✅ Preserves File Integrity
- **Formulas**: All calculations and formulas remain intact (Numbers & Excel)
- **Formatting**: Cell colors, fonts, and styles preserved
- **Table Structure**: Headers, column widths, and layout unchanged
- **Data Types**: Numbers remain numbers, text remains text
- **Round-Trip**: Numbers files converted via Excel maintain full fidelity

### 🔒 Safety Features
- **Automatic Cleanup**: Removes temporary files after successful processing
- **Dry Run Mode**: Analyze changes without applying them
- **Error Recovery**: Preserves intermediate files if conversion fails
- **Dependency Checking**: Validates required tools (openpyxl, Numbers app)
- **Non-destructive**: Original file preserved unless explicitly overwritten

### 🎯 Smart Detection
- **Column Detection**: Automatically finds "Value" and "IPN" columns
- **Targeted Changes**: Only modifies values that need Unicode normalization
- **Progress Reporting**: Shows exactly what will be/was changed

## Usage Examples

### Safe Analysis (Recommended First Step)
```bash
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py poc/inventory-enhancement/examples/test-search-INVENTORY.numbers --dry-run
```
Output for all file types:
```
=== INVENTORY FIX ANALYSIS ===
Input file: test-search-INVENTORY.numbers
Total items: 96
Items needing fixes: 21
Categories affected: RES

=== FIXES TO BE APPLIED ===
  RES_5%_100mW_0603_1kΩ (RES): '1kΩ' → '1k'
  RES_5%_100mW_0603_2.2kΩ (RES): '2.2kΩ' → '2.2k'
  ...

=== DRY RUN COMPLETE ===
To apply these fixes, run with --apply flag
```

**For Numbers files, the workflow would be:**
```
📋 Would perform:
   1. Export Numbers file to Excel (preserves formulas)
   2. Apply Unicode fixes to Excel file
   3. Open fixed Excel file in Numbers
   4. Save as .numbers format
   5. Clean up temporary Excel file

💡 Result: Fixed .numbers file with preserved formulas
```

### Create New Fixed File
```bash
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py poc/inventory-enhancement/examples/test-search-INVENTORY.numbers \
    --output poc/inventory-enhancement/examples/test-search-INVENTORY-normalized.numbers \
    --apply
```

### In-Place Modification (Default Behavior)
```bash
python poc/inventory-enhancement/scripts/apply_inventory_fixes.py poc/inventory-enhancement/examples/test-search-INVENTORY.numbers --apply
```

This creates:
- `test-search-INVENTORY.numbers` (updated with fixes)
- `test-search-INVENTORY-backup-2025-12-22_00-56-30.numbers` (timestamped backup)

**Note**: The original file is updated in-place with a timestamped backup for safety.

## How It Works

### Numbers Files: Automated Round-Trip Workflow
Numbers files use a sophisticated round-trip process to preserve formulas:

1. **Export**: Numbers file → Excel (.xlsx) using AppleScript
2. **Process**: Apply Unicode fixes to Excel file (preserves formulas)
3. **Import**: Open Excel in Numbers and save as .numbers format
4. **Cleanup**: Remove temporary Excel files

**Advantages:**
- Preserves all formulas and formatting
- Fully automated (no manual steps)
- Creates proper Numbers file output
- Handles complex spreadsheet features

**Requirements:**
- macOS with Numbers app installed
- openpyxl Python package (`pip install openpyxl`)
- AppleScript automation permissions

### Excel Files: Direct Modification
Excel files are modified directly using openpyxl:

1. Load Excel file with formula preservation
2. Find "Value" column and apply Unicode fixes
3. Save with all formatting intact

### CSV Files: Text Processing
CSV files use simple text replacement:

1. Load as text with UTF-8 encoding
2. Apply Unicode symbol replacements
3. Save with automatic backup

## Error Handling

### Common Issues and Solutions

**"Excel support not available (openpyxl not installed)"**
```bash
pip install openpyxl
```

**"Error loading Numbers file"**
- File might be corrupted or password protected
- Try opening in Numbers app first to verify it's accessible

**"Could not find 'Value' column"**
- Verify your Numbers file has a column header exactly named "Value"
- Column detection is case-sensitive

**File permission errors**
- Ensure you have write access to the output directory
- Close the Numbers file in Numbers app before running script

## Validation

After applying fixes, validate the results:

```bash
# Test the fixed inventory with distributor search (from jBOM root)
python -m jbom inventory-search poc/inventory-enhancement/examples/test-search-INVENTORY-fixed.numbers --dry-run
```

Expected result: 100% search success rate on electronic components.

## Integration with jBOM Workflow

Once your inventory is normalized:

```bash
# Generate enhanced inventory with distributor data (from jBOM root)
python -m jbom inventory-search poc/inventory-enhancement/examples/test-search-INVENTORY-fixed.numbers \
    --output enhanced-inventory.csv \
    --limit 3

# Use in BOM generation
python -m jbom bom project/ -i poc/inventory-enhancement/examples/test-search-INVENTORY-fixed.numbers
```

## Best Practices

1. **Always run dry-run first** to see what will be changed
2. **Backup important files** before making changes
3. **Test with distributor search** after applying fixes
4. **Update component libraries** in KiCad to use ASCII values
5. **Document changes** for your team

## File Support
| Format | Read | Write | Formulas | Formatting | Method | Notes |
|--------|------|-------|----------|------------|--------|---------|
| .numbers | ✅ | ✅ | ✅ | ✅ | AppleScript Round-Trip | Via Excel conversion (automated) |
| .xlsx/.xls | ✅ | ✅ | ✅ | ✅ | Direct openpyxl | Native Excel modification |
| .csv | ✅ | ✅ | ❌ | ❌ | Text Processing | Simple text replacement |
| .csv | ✅ | ✅ | ❌ | ❌ | ✅ | Text format - cannot preserve spreadsheet features |

### Format Recommendations
- **Numbers/Excel**: Use for inventory with formulas, formatting, or complex structure
- **CSV**: Use for simple inventory or when maximum compatibility is needed
- **All formats** support automatic backup when modifying original files

## Troubleshooting

### Script hangs or crashes
- Ensure Numbers app is not open with the file
- Check file permissions
- Try with a smaller test file first

### Changes not applied
- Verify you used `--apply` flag (not just `--dry-run`)
- Check that the "Value" column exists and is named correctly
- Ensure you have write permissions

### Formula corruption (unlikely)
- This script only modifies cell values in the "Value" column
- Formulas in other columns remain untouched
- If you experience issues, restore from backup

### Getting Help

Create an issue with:
- Command you ran
- Error message (if any)
- Sample of your Numbers file structure (screenshot of headers)
- Operating system and Python version
