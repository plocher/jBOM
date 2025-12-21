#!/bin/bash
#
# Test search functionality with entire inventory - CLI version
#
# Iterates through every item in the example inventory and uses 'jbom search'
# to find the 3 best Mouser parts for each item. This should expose the same
# issues as the Python API test, validating implementation consistency.
#

set -e

echo "🔍 jBOM Inventory Search Test - CLI"
echo "=================================="

# Check for API key
if [[ -z "$MOUSER_API_KEY" ]]; then
    echo "❌ MOUSER_API_KEY environment variable required"
    echo "   Set it with: export MOUSER_API_KEY=your_key"
    exit 1
fi

echo "✅ Found MOUSER_API_KEY"

# Set up paths
JBOM_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$JBOM_DIR"

echo "📁 Working from: $JBOM_DIR"

# First, extract inventory data to CSV for easier processing
echo "📋 Loading inventory data..."
INVENTORY_CSV="examples/temp_inventory_for_test.csv"

PYTHONPATH="$JBOM_DIR/src:$PYTHONPATH" python3 -c "
from jbom.loaders.inventory import InventoryLoader
from pathlib import Path
import csv

# Load inventory
loader = InventoryLoader(Path('examples/example-INVENTORY.numbers'))
items, _ = loader.load()

# Write simplified CSV for bash processing
with open('examples/temp_inventory_for_test.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['IPN', 'Category', 'Value', 'Package', 'MFGPN'])

    for item in items:
        writer.writerow([
            item.ipn,
            item.category,
            item.value or '',
            item.package or '',
            getattr(item, 'mfgpn', '') or ''
        ])

print(f'✅ Exported {len(items)} items to temp CSV')
"

# Test stats
declare -i total_items=0
declare -i items_searched=0
declare -i successful_searches=0
declare -i good_results=0
declare -i no_query=0
declare -i no_results=0
declare -i errors=0

echo ""
echo "🎯 Testing 'jbom search' CLI for all inventory items..."

# Process each inventory item
while IFS=',' read -r ipn category value package mfgpn || [[ -n "$ipn" ]]; do
    # Skip header
    if [[ "$ipn" == "IPN" ]]; then
        continue
    fi

    ((total_items++))
    echo ""
    echo "--- $total_items: $ipn ($category) ---"

    # Build search query - same logic as Python version
    query=""
    strategy=""

    # Use existing MPN if available (best case)
    if [[ -n "$mfgpn" && "$mfgpn" != "N/A" ]]; then
        query="$mfgpn"
        strategy="mpn"
    else
        # Build from component data
        terms=()

        if [[ -n "$value" && "$value" != "N/A" ]]; then
            # Skip obvious non-components
            if [[ ! "$value" =~ (BRD_|DCPower|EDG-104) ]]; then
                terms+=("$value")
            fi
        fi

        if [[ -n "$package" && "$package" != "N/A" ]]; then
            # Add common package types
            if [[ "$package" =~ (0603|0805|1206|SOT|SOP|SOIC) ]]; then
                terms+=("$package")
            fi
        fi

        # Add category-specific terms
        case "$category" in
            RES) terms+=("resistor") ;;
            CAP) terms+=("capacitor") ;;
            LED) terms+=("LED") ;;
            IC) terms+=("integrated circuit") ;;
            Q) terms+=("transistor") ;;
            DIO) terms+=("diode") ;;
            REG) terms+=("voltage regulator") ;;
            MCU) terms+=("microcontroller") ;;
        esac

        # Join terms
        query="${terms[*]}"
        strategy="constructed"
    fi

    if [[ -z "$query" ]]; then
        echo "⚠️  No searchable data"
        ((no_query++))
        continue
    fi

    echo "Query: '$query' ($strategy)"
    ((items_searched++))

    # Run jbom search - this is the core test!
    if search_output=$(PYTHONPATH="$JBOM_DIR/src:$PYTHONPATH" python -m jbom search "$query" --limit 3 2>/dev/null); then
        # Check if results were found
        if echo "$search_output" | grep -q "No results found"; then
            echo "❌ No results"
            ((no_results++))
        else
            echo "✅ Search succeeded"
            ((successful_searches++))

            # Count results (look for lines with manufacturer/part info)
            result_count=$(echo "$search_output" | grep -c "│.*│.*│.*│" | head -1 || echo "0")

            if [[ $result_count -ge 3 ]]; then
                ((good_results++))
            fi

            # Show first few results
            echo "$search_output" | head -8
        fi
    else
        echo "❌ Search failed"
        ((errors++))
    fi

    # Rate limiting
    sleep 0.5

done < "$INVENTORY_CSV"

# Results summary
echo ""
echo "========================================="
echo "📊 CLI TEST RESULTS"
echo "========================================="

echo "Total items: $total_items"
echo "Items searched: $items_searched"
echo "Successful searches: $successful_searches"
echo "Good results (3+ parts): $good_results"
echo "No searchable data: $no_query"
echo "No results found: $no_results"
echo "Search errors: $errors"

if [[ $items_searched -gt 0 ]]; then
    success_rate=$((successful_searches * 100 / items_searched))
    good_rate=$((good_results * 100 / items_searched))
    echo ""
    echo "Success rate: ${success_rate}%"
    echo "Good results rate: ${good_rate}%"
fi

echo ""
echo "🎯 CONSISTENCY CHECK:"
echo "Run both tests and compare results to verify CLI and Python API consistency!"

# Cleanup
rm -f "$INVENTORY_CSV"

exit 0
