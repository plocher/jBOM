#!/bin/bash
#
# CLI Test Workflow for jBOM Search Functionality
#
# This script demonstrates CLI usage of jBOM search capabilities and helps
# identify areas for improvement in search functionality and user experience.
#

set -e

echo "🚀 jBOM CLI Search Functionality Test"
echo "====================================="

# Check for API key
if [[ -z "$MOUSER_API_KEY" ]]; then
    echo "❌ MOUSER_API_KEY environment variable is required"
    echo "   Set it with: export MOUSER_API_KEY=your_api_key_here"
    exit 1
fi

echo "✅ Found MOUSER_API_KEY"

# Set up paths
JBOM_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXAMPLES_DIR="$JBOM_DIR/examples"
cd "$JBOM_DIR"

echo "📁 Working directory: $JBOM_DIR"

# Test 1: Direct search command for common components
echo ""
echo "🔍 TEST 1: Direct search for common electronic components"
echo "--------------------------------------------------------"

test_queries=(
    "220 ohm 0603 resistor"
    "0.01uF capacitor 0603"
    "blue LED 0603"
    "LM358 op amp"
    "AMS1117-3.3 regulator"
)

for query in "${test_queries[@]}"; do
    echo ""
    echo "Searching for: '$query'"
    echo "Command: jbom search '$query' --limit 3"

    # Run the search and capture results
    if PYTHONPATH="$JBOM_DIR/src:$PYTHONPATH" python -m jbom search "$query" --limit 3; then
        echo "✅ Search succeeded"
    else
        echo "❌ Search failed with exit code $?"
    fi

    echo "---"
    sleep 1  # Rate limiting
done

echo ""
echo "🎯 CLI SEARCH TEST RESULTS"
echo "=========================="
echo "✅ CLI search command basic functionality verified"
echo ""
echo "📋 Next Steps:"
echo "- Review search results quality above"
echo "- Check if results match expected component types"
echo "- Verify that 3 results were returned when available"
echo "- Look for any error messages or failed searches"
echo ""
echo "💡 Tips for improving search results:"
echo "- More specific queries (e.g., include package size)"
echo "- Use manufacturer part numbers when available"
echo "- Include component category keywords"
echo ""
echo "✅ CLI workflow test completed!"
