# Comprehensive Fault Testing Scenarios - Future Implementation

## Context
During BDD scenario review, identified need for comprehensive edge case and fault testing scenarios that force policy decisions to be documented explicitly in BDD scenarios.

## Key Insight
> "This type of fault testing should be extended to all the BDD scenarios here. It may be obvious, but these types of tests will find bugs in the existing jBOM code base; it must be unambiguous as to what the expected outcome is for these vectors."

## Critical Policy Questions That Need BDD Specification

### Priority Field Invalid Data Policy
- **Single item with invalid priority**: Should it still match? (Answer: Yes, with warning)
- **Multiple candidates, some invalid**: How to handle mixed valid/invalid priorities?
- **All candidates invalid**: Fall back to source order? Alphabetical? Error?
- **Specific invalid values**: negative numbers, non-numeric text, empty strings

### Edge Case Vectors to Test
**Priority Values:**
- Numeric: 0, 2147483647, 4294967295, -1, -999
- Power-of-2 boundaries: 255, 256, 65535, 65536, 1024
- Spreadsheet malformed: "1", "01", "1.0", "1,000", "", " 5 ", "high", "#DIV/0!", "NULL"

**All Fields Need Fault Testing:**
- **Category**: "", "INVALID", 123, "R&C"
- **Value**: "", "10k ohm", "∞", "<1"
- **Package**: "", "custom package", "0603/0805"
- **Distributor**: "", "My Local Shop", "JLC_PCB"
- **IPN**: "", duplicates, "IPN with spaces"

### Required Scenario Pattern
```gherkin
Scenario: [Specific fault condition]
  Given [explicit test vectors showing fault]
  When I generate a BOM
  Then [exact expected behavior - not "handle gracefully"]
  And [specific warnings/errors expected]
```

## Implementation Approach
1. **Policy First**: Define expected behavior in BDD scenarios before implementation
2. **Comprehensive Coverage**: Test every field type with malformed data
3. **Real-World Focus**: Test actual spreadsheet corruption patterns
4. **Explicit Expectations**: No vague "handle gracefully" - specify exact behavior

## Integration Point
These fault testing scenarios should be integrated across ALL existing BDD features:
- component_matching.feature
- multi_source_inventory.feature
- priority_selection.feature
- fabricator_formats.feature
- All other feature files

## Critical Gap: File Processing vs Logic Testing

### Current BDD Scenarios Only Test Logic
Existing BDD scenarios test business logic (priority selection, fabricator filtering, component matching) but **NOT actual file parsing** that feeds data into that logic.

### Missing File Processing Coverage
**KiCad File Parsing:**
- `.kicad_sch` S-expression parsing with real KiCad projects
- Hierarchical schematic handling (sub-sheets)
- Component extraction from actual KiCad files

**Inventory File Parsing:**
- **Excel (.xlsx/.xls)**: Real Excel exports with formulas, multiple sheets
- **Numbers**: Actual Apple Numbers file format
- **CSV**: Real CSV exports with various delimiters and encoding

### BDD vs Unit Test Boundaries

**BDD Scenarios Should Test (User Workflows):**
```gherkin
Scenario: Generate BOM using Excel inventory file
  Given a KiCad project "MyBoard"
  And an Excel inventory file "parts_database.xlsx"
  When I generate a BOM
  Then the BOM contains matched components from Excel data
```

**Unit Tests Should Test (Implementation Details):**
- CSV delimiter detection, quoted fields, encoding
- Excel formula evaluation, merged cells
- S-expression parsing edge cases
- Column header mapping variations

**Integration Point:** Add end-to-end file processing scenarios to `annotate/` and `bom/` features that test real file format workflows.

## Future Task
Create comprehensive fault testing scenarios that force policy decisions to be documented explicitly, ensuring jBOM behavior is unambiguous for all edge cases and malformed input data.
