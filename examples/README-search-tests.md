# jBOM Search Functionality Test Workflows

These test workflows validate jBOM's search capabilities by finding the "3 best" Mouser parts for every item in the example inventory. This comprehensive testing approach exposes both inventory data quality issues and search algorithm limitations.

## Overview

These tests serve three critical purposes:

1. **Search Validation**: Verify search functionality works with real inventory data
2. **Failure Mode Analysis**: Expose inventory data quality vs. search algorithm issues
3. **Implementation Consistency**: Ensure CLI and Python API produce consistent results

## Prerequisites

### API Key Setup
You'll need a Mouser API key for these tests:

```bash
export MOUSER_API_KEY=your_mouser_api_key_here
```

You can get a free API key from [Mouser's API portal](https://www.mouser.com/api-hub/).

### Dependencies
Ensure jBOM is set up for development:

```bash
# From the jBOM root directory
pip install -e .[dev,search,all]
```

## Test Workflows

### 1. Python API Test (`test_inventory_search.py`)

**Purpose**: Tests `search_parts()` API with every inventory item.

**What it does**:
- Loads ALL items from `example-INVENTORY.numbers` (96 components)
- For each item, builds a search query from available data
- Uses `search_parts(limit=3)` to find 3 best Mouser parts
- Tracks success rates, data quality issues, and algorithm limitations
- Provides category-by-category analysis

**Run it**:
```bash
cd examples/
python test_inventory_search.py
```

**Expected Output**:
- Component-by-component search results
- Success rate statistics
- Recommendations for improvements
- Identification of problematic inventory entries

### 2. CLI Test (`test_inventory_cli.sh`)

**Purpose**: Tests `jbom search` CLI with every inventory item.

**What it does**:
- Loads ALL items from `example-INVENTORY.numbers` (same 96 components)
- Uses identical search query logic as Python test
- Runs `jbom search "query" --limit 3` for each item
- Should produce consistent results with Python API test
- Validates CLI and API implementation consistency

**Run it**:
```bash
cd examples/
./test_inventory_cli.sh
```

**Expected Output**:
- Search results for each test query
- CLI functionality verification
- User experience assessment

## Test Components

The workflows focus on these component categories from the inventory:

| Category | Examples | Expected Search Quality |
|----------|----------|------------------------|
| **RES** | 220Ω 0603, 200Ω 0603 | ✅ High (common values) |
| **CAP** | 0.01uF 0603 | ✅ High (standard caps) |
| **LED** | Blue 0603, White 0603 | ✅ High (common LEDs) |
| **IC** | LM358D, NE556 | ✅ High (popular ICs) |
| **Q** | MMBT2222, BC807 | ✅ High (standard BJTs) |
| **DIO** | BAT54, 4.7V Zener | ✅ High (common diodes) |

## Success Criteria

### Functional Success
- [ ] API searches complete without errors
- [ ] CLI commands execute successfully
- [ ] Search results are returned for most queries
- [ ] No crashes or timeouts

### Quality Success
- [ ] ≥80% of searches return results
- [ ] ≥60% of searches return 3+ results
- [ ] Results match expected component types
- [ ] Price and stock information is available

### User Experience Success
- [ ] Clear error messages for failed searches
- [ ] Reasonable response times (<5s per search)
- [ ] Intuitive CLI interface
- [ ] Helpful result formatting

## Interpreting Results

### Good Results 👍
```
✅ Found 3 results:
  1. Yageo RC0603FR-07220RL
     Description: RES SMD 220 OHM 1% 1/10W 0603
     Price: $0.10
     Stock: 1000+
```

### Areas for Improvement 🔧

**Empty Results**:
```
❌ No results found
```
→ Search query may be too specific or inventory data incomplete

**API Errors**:
```
❌ Search failed: Invalid API key
```
→ Check API key setup and network connectivity

**Poor Quality Results**:
```
⚠️ Found 1 result (expected 3)
```
→ Consider broader search terms or query refinement

## Files

- `test_search_workflow.py` - Python API comprehensive test
- `test_cli_search.sh` - CLI functionality test
- `example-INVENTORY.numbers` - Source inventory data (96 components)
- `test-search-INVENTORY.numbers` - Test copy (safe to modify)

## Real-World Impact

These tests help ensure that when users run:

```bash
jbom inventory MyProject/ --search --limit 3
```

They get:
- ✅ Reliable search results
- ✅ Quality part recommendations
- ✅ Useful error messages
- ✅ Reasonable performance

## Next Steps After Testing

Based on test results, consider:

1. **Query Optimization**: Improve search term generation
2. **Inventory Data**: Enhance component specifications
3. **Error Handling**: Better user guidance for failed searches
4. **Performance**: Caching or batch optimizations
5. **Coverage**: Support for additional component categories

---

**Run both workflows before merging the search automation feature to ensure production readiness! 🚀**
