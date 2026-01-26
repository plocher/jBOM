# jBOM Testing Guidelines

## Lessons Learned from Spring Cleaning

This document captures insights from stabilizing the jBOM Behave test suite to prevent future test debt accumulation.

## Core Testing Principles

### 1. Test Behavior, Not Implementation

**✅ Good: Tests the contract**
```gherkin
When I run jbom command "bom --inventory A.csv --inventory A.csv"
Then the output should contain exactly one "RES_10K" entry
```

**❌ Bad: Tests implementation details**
```gherkin
When I run jbom command "bom --inventory A.csv --inventory A.csv"
Then the system should detect duplicate filenames and skip the second file
```

**Why**: Implementation can change (file caching vs record deduplication vs hash-based) while maintaining the same functional contract.

### 2. Avoid Semantic Coupling in Step Names

**✅ Good: Neutral, data-focused**
```gherkin
Given an inventory file "A.csv" with contents:
And an inventory file "B.csv" with contents:
```

**❌ Bad: Implies business logic**
```gherkin
Given a primary inventory file "primary.csv" with contents:
And a secondary inventory file "secondary.csv" with contents:
```

**Why**: Step names like "primary/secondary" encode assumptions about precedence rules that may not exist or may change.

### 3. Test Distinguishable Scenarios

**✅ Good: Tests actual precedence with different data**
```gherkin
Given an inventory file "A.csv" with contents:
  | IPN     | Manufacturer |
  | RES_10K | Yageo        |
And an inventory file "B.csv" with contents:
  | IPN     | Manufacturer |
  | RES_10K | Vishay       |
When I run jbom command "bom --inventory A.csv --inventory B.csv"
Then the output should contain "Yageo"
```

**❌ Bad: Identical data can't test precedence**
```gherkin
Given an inventory file "A.csv" with contents:
  | IPN     | Value |
  | RES_10K | 10k   |
And an inventory file "B.csv" with contents:
  | IPN     | Value |
  | RES_10K | 10k   |
# This test proves nothing - identical data has identical outcome
```

### 4. Include Domain Context

**✅ Good: Explicit fabricator context**
```gherkin
Background:
  Given the generic fabricator is selected
```

**❌ Bad: Missing critical context**
```gherkin
# Fabricator selection affects filtering, but it's not specified
When I run jbom command "bom --inventory components.csv"
```

**Why**: jBOM behavior depends on fabricator selection for filtering and matching logic.

## Current State Assessment

### What We Fixed ✅
- **Step Definition Coverage**: 0 undefined steps (from ~450)
- **Syntactic Redundancy**: Consolidated verbose patterns like "primary/secondary/tertiary inventory file"
- **Legacy Adapter Cleanup**: Removed ~15 redundant patterns
- **Schematic Creation Consolidation**: Unified "BOM test/minimal test" variants

### What We Discovered ❌
- **Wrong Tool Testing**: Some tests use `jbom inventory` when they should use `jbom bom`
- **Questionable Business Logic**: "Precedence" behavior may be incorrect deduplication
- **Missing Deduplication Tests**: Basic identical-record scenarios not covered
- **Format Obsession**: Many tests focus on CSV vs table format instead of data content

## Next Steps Priority Order

### Phase 1: Validate Business Logic
1. **Test basic deduplication**: `--inventory A.csv --inventory A.csv` should deduplicate
2. **Verify tool usage**: Ensure `jbom inventory` vs `jbom bom` tests are using correct commands
3. **Check precedence logic**: Verify if "precedence" is actually broken deduplication

### Phase 2: Execute and Debug
1. **Run passing features**: Identify which scenarios actually work
2. **Fix step implementations**: Address scenarios that fail due to implementation gaps
3. **Add missing core scenarios**: Fill gaps in basic functionality coverage

### Phase 3: Eliminate Over-specification
1. **Remove format paranoia**: Focus on data content, not output format details
2. **Simplify complex scenarios**: Break down over-specified tests into focused ones
3. **Add missing edge cases**: Cover error conditions and boundary cases

## Anti-Patterns to Avoid

### 1. Semantic Step Name Pollution
```gherkin
# ❌ DON'T: Encode business logic in step names
Given a primary inventory file "..." with contents:
Given a high-priority inventory file "..." with contents:
Given a preferred inventory file "..." with contents:

# ✅ DO: Use neutral, data-focused names
Given an inventory file "..." with contents:
```

### 2. Implementation Detail Testing
```gherkin
# ❌ DON'T: Test how it works
Then the system should merge files in precedence order
Then the cache should contain the inventory data

# ✅ DO: Test what it does
Then the output should contain all unique components
Then RES_10K should have manufacturer "Yageo"
```

### 3. No-Op Testing
```gherkin
# ❌ DON'T: Test scenarios with identical outcomes
Given file A contains: RES_10K,10k,Yageo
Given file B contains: RES_10K,10k,Yageo
Then precedence should favor file A
# ^ This proves nothing since both outcomes are identical

# ✅ DO: Test scenarios with distinguishable outcomes
Given file A contains: RES_10K,10k,Yageo
Given file B contains: RES_10K,10k,Vishay
Then the output should contain "Yageo"
```

## Step Definition Architecture

### Current Structure
- **Canonical steps**: Core business logic in `common_steps.py`
- **Legacy adapter**: Backward compatibility in `legacy_compat.py`
- **Domain-specific**: BOM, POS, inventory steps in separate files

### Legacy Adapter Guidelines
- **Purpose**: Provide backward compatibility during migration only
- **TODO marker**: All legacy adapters should delegate to canonical implementations
- **Cleanup target**: Remove legacy adapter after feature file migration
- **No business logic**: Legacy adapters should never contain core logic

## Testing Command Patterns

### BOM Generation
```gherkin
# Project → BOM (with optional inventory enhancement)
When I run jbom command "bom"                                    # Basic BOM
When I run jbom command "bom --inventory components.csv"         # Enhanced BOM
When I run jbom command "bom --fabricator jlc"                  # Fabricator-specific
```

### Inventory Operations
```gherkin
# Project → Inventory file (extract components)
When I run jbom command "inventory"                              # Generate inventory
When I run jbom command "inventory --filter-matches"            # Show unmatched only
```

### POS Generation
```gherkin
# Project → POS file (placement data)
When I run jbom command "pos"                                    # Basic POS
When I run jbom command "pos --fabricator jlc"                  # Fabricator-specific
```

## File Naming Conventions

### Inventory Files
- Use descriptive names: `components.csv`, `resistors.csv`, `capacitors.csv`
- Avoid semantic implications: Not `primary.csv`, `secondary.csv`
- For multiple files: Use neutral names `A.csv`, `B.csv`, `C.csv` when testing merging logic

### Project Files
- Use anonymous projects when possible: Let scenarios create inline component tables
- Use named projects only when testing project discovery or file-specific behavior
- Background should set up feature-wide projects to avoid repetition

## Assertion Guidelines

### Focus on Business Value
```gherkin
# ✅ Good: Tests business outcome
Then the BOM should contain component "R1" with value "10K"
Then all schematic components should be included

# ❌ Bad: Tests implementation details
Then the output should be in CSV format
Then the file should have exactly 3 columns
```

### Content Over Format
- Test that data is present and correct
- Don't obsess over CSV vs table formatting
- Format testing should be limited to explicit UX requirements (like `ux_consistency.feature`)

## Success Metrics

### Definition of Done
- [ ] **All steps defined**: 0 undefined steps across all features
- [ ] **Core scenarios pass**: Basic BOM, POS, inventory generation works
- [ ] **Edge cases covered**: Error conditions, empty projects, missing files handled
- [ ] **Business logic validated**: Deduplication, fabricator filtering, file merging works correctly

### Quality Gates
- **No format obsession**: <5% of assertions should be about output format
- **No semantic coupling**: Step names should not imply business logic
- **No no-op tests**: All scenarios should test distinguishable outcomes
- **Domain context included**: All scenarios should specify fabricator/context when relevant

## Current Status
- **Step Definitions**: ✅ Complete (0 undefined)
- **Business Logic Validation**: ❓ Needs investigation
- **Execution Testing**: ❓ Not started
- **Core Functionality**: ❓ Unknown pass rate

---

*This document should be updated as we learn more about the actual jBOM business requirements and fix the underlying implementation.*
