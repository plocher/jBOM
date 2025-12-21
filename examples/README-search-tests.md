# jBOM Search Functionality Test Workflows

This directory contains comprehensive test workflows to validate and evaluate jBOM's search automation capabilities before merging the inventory search automation feature.

## Overview

These tests serve two critical purposes:

1. **Validation**: Verify that the search functionality works correctly with real-world components
2. **Quality Assessment**: Identify areas where search algorithms or inventory data could be improved

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

### 1. Python API Workflow (`test_search_workflow.py`)

**Purpose**: Tests the `search_parts()` API function with real inventory components.

**What it does**:
- Loads components from `example-INVENTORY.numbers`
- Focuses on searchable categories: RES, CAP, LED, IC, Q, DIO
- Searches for the "3 best" Mouser parts for each component
- Provides detailed analysis of search success rates and result quality

**Run it**:
```bash
cd examples/
python test_search_workflow.py
```

**Expected Output**:
- Component-by-component search results
- Success rate statistics
- Recommendations for improvements
- Identification of problematic inventory entries

### 2. CLI Workflow (`test_cli_search.sh`)

**Purpose**: Tests the `jbom search` CLI command with representative queries.

**What it does**:
- Tests common electronic component searches
- Validates CLI argument handling and output formatting
- Demonstrates typical user workflows

**Run it**:
```bash
cd examples/
./test_cli_search.sh
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
