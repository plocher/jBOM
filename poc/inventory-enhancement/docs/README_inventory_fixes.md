# Inventory Unicode Normalization Fix Guide

This guide shows how to apply Unicode normalization fixes to your Numbers inventory file while preserving formulas, formatting, and table structure.

## Quick Start

### Numbers Files (Preserves Formulas & Formatting)
```bash
# 1. Analyze what fixes are needed (safe, no changes)
python apply_inventory_fixes.py examples/example-INVENTORY.numbers --dry-run

# 2. Apply fixes to create a new fixed file
python apply_inventory_fixes.py examples/example-INVENTORY.numbers --output examples/example-INVENTORY-fixed.numbers --apply

# 3. Apply fixes directly to original (creates backup automatically)
python apply_inventory_fixes.py examples/example-INVENTORY.numbers --apply
```

### Excel Files (Preserves Formulas & Formatting)
```bash
# Analyze Excel inventory
python apply_inventory_fixes.py inventory.xlsx --dry-run

# Fix Excel file with backup
python apply_inventory_fixes.py inventory.xlsx --apply

# Create new fixed Excel file
python apply_inventory_fixes.py inventory.xlsx --output inventory-fixed.xlsx --apply
```

### CSV Files (Text Format Only)
```bash
# Analyze CSV inventory
python apply_inventory_fixes.py inventory.csv --dry-run

# Fix CSV with automatic backup
python apply_inventory_fixes.py inventory.csv --apply
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

### ✅ Preserves Numbers File Integrity
- **Formulas**: All calculations and formulas remain intact
- **Formatting**: Cell colors, fonts, and styles preserved
- **Table Structure**: Headers, column widths, and layout unchanged
- **Data Types**: Numbers remain numbers, text remains text

### 🔒 Safety Features
- **Automatic Backup**: Creates backup file when modifying original
- **Dry Run Mode**: Analyze changes without applying them
- **Error Recovery**: Fallback to CSV approach if direct modification fails
- **Non-destructive**: Original file preserved unless explicitly overwritten

### 🎯 Smart Detection
- **Column Detection**: Automatically finds "Value" and "IPN" columns
- **Targeted Changes**: Only modifies values that need Unicode normalization
- **Progress Reporting**: Shows exactly what will be/was changed

## Usage Examples

### Safe Analysis (Recommended First Step)
```bash
python apply_inventory_fixes.py examples/example-INVENTORY.numbers --dry-run
```
Output:
```
=== INVENTORY FIX ANALYSIS ===
Input file: examples/example-INVENTORY.numbers
Total items: 96
Items needing fixes: 21
Categories affected: RES

=== FIXES TO BE APPLIED ===
  RES_5%_100mW_0603_1kΩ (RES): '1kΩ' → '1k'
  RES_5%_100mW_0603_2.2kΩ (RES): '2.2kΩ' → '2.2k'
  ...
```

### Create New Fixed File
```bash
python apply_inventory_fixes.py examples/example-INVENTORY.numbers \
    --output examples/example-INVENTORY-normalized.numbers \
    --apply
```

### Modify Original (with Automatic Backup)
```bash
python apply_inventory_fixes.py examples/example-INVENTORY.numbers --apply
```

This creates:
- `example-INVENTORY-backup.numbers` (original file)
- `example-INVENTORY.numbers` (updated with fixes)

## How It Works

### Method 1: Direct Numbers Modification (Preferred)
1. Loads the Numbers file using numbers-parser
2. Finds the "Value" column in the table
3. Iterates through each row looking for Unicode symbols
4. Replaces symbols with ASCII equivalents
5. Saves the modified Numbers file

**Advantages:**
- Preserves all formulas and formatting
- Fast and reliable
- Creates proper Numbers file output

### Method 2: CSV Fallback (If Needed)
If direct modification fails, the script:
1. Exports Numbers data to CSV
2. Applies fixes to CSV
3. Provides instructions for manual import back to Numbers

**When Used:**
- File permission issues
- Unsupported Numbers file format
- Other technical limitations

## Error Handling

### Common Issues and Solutions

**"Error: numbers-parser not available"**
```bash
pip install numbers-parser
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
# Test the fixed inventory with distributor search
python -m jbom inventory-search examples/example-INVENTORY-fixed.numbers --dry-run
```

Expected result: 100% search success rate on electronic components.

## Integration with jBOM Workflow

Once your inventory is normalized:

```bash
# Generate enhanced inventory with distributor data
python -m jbom inventory-search examples/example-INVENTORY-fixed.numbers \
    --output enhanced-inventory.csv \
    --limit 3

# Use in BOM generation
python -m jbom bom project/ -i examples/example-INVENTORY-fixed.numbers
```

## Best Practices

1. **Always run dry-run first** to see what will be changed
2. **Backup important files** before making changes
3. **Test with distributor search** after applying fixes
4. **Update component libraries** in KiCad to use ASCII values
5. **Document changes** for your team

## File Support

| Format | Read | Write | Formulas | Formatting | Backup | Notes |
|--------|------|-------|----------|------------|--------|---------|
| .numbers | ✅ | ✅ | ✅ | ✅ | ✅ | Full Numbers support with Apple Numbers parser |
| .xlsx/.xls | ✅ | ✅ | ✅ | ✅ | ✅ | Full Excel support with openpyxl |
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
