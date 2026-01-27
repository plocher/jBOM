# Efficient Behave Development Workflow

This guide shows efficient development patterns for working with Behave tests, especially when combined with KiCad validation.

## The Rerun Pattern for Development

### Problem: Slow Full Suite Runs
Running the full test suite repeatedly during development is inefficient:
```bash
behave  # Runs all 192 scenarios, takes time
# Fix one issue
behave  # Runs all 192 scenarios again, mostly passing
```

### Solution: Focus on Failures with Rerun Formatter
```bash
# 1. Run full suite, capture failures
behave -f rerun -o failed_scenarios.txt

# 2. Work only on failures
behave @failed_scenarios.txt

# 3. Repeat until clean
behave @failed_scenarios.txt
```

## Practical Development Workflow

### Phase 1: Initial Assessment
```bash
# Run full suite with validation to identify all issues
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o failed_scenarios.txt --no-capture
```

This creates `failed_scenarios.txt` with just the failing scenarios:
```
features/bom/core.feature:23
features/pos/generation.feature:45
features/validation/seamless_validation_example.feature:16
```

### Phase 2: Focused Development
```bash
# Work only on failures - much faster iteration
behave @failed_scenarios.txt

# Example output shows only the failing scenarios:
# 3 scenarios (0 passed, 3 failed, 189 skipped)
```

### Phase 3: Iterative Fixing
```bash
# Fix issues, re-run just failures
behave @failed_scenarios.txt

# As you fix issues, the failure list shrinks
# 2 scenarios (1 passed, 1 failed, 190 skipped)

# Continue until clean
behave @failed_scenarios.txt
# 0 scenarios (2 passed, 0 failed, 190 skipped)
```

### Phase 4: Final Validation
```bash
# When failures are clean, run full suite to confirm
behave
# All 192 scenarios should pass
```

## Integration with KiCad Validation

### Validation-Focused Development
```bash
# 1. Enable validation and identify all fake KiCad content
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o kicad_failures.txt

# 2. Focus on KiCad validation failures only
behave @kicad_failures.txt
# Enhanced diagnostics show exactly what needs fixing

# 3. Fix fake content based on diagnostic guidance
# 4. Re-run validation failures
behave @kicad_failures.txt

# 5. When validation clean, turn off validation and test functionality
unset JBOM_VALIDATE_KICAD
behave @kicad_failures.txt  # Should still pass without validation
```

### Mixed Development Approach
```bash
# Run with validation to catch both functional AND authenticity issues
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o all_failures.txt

# Work on all failures (functional + validation)
behave @all_failures.txt

# This approach fixes both types of issues simultaneously
```

## Advanced Patterns

### Tag-Based Failure Focus
```bash
# Focus on specific failure types
behave --tags @validation -f rerun -o validation_failures.txt
behave @validation_failures.txt

# Or focus on core functionality
behave --tags @regression -f rerun -o regression_failures.txt
behave @regression_failures.txt
```

### Incremental Development
```bash
# Start with a subset, ensure it's clean
behave features/bom/ -f rerun -o bom_failures.txt
behave @bom_failures.txt

# Expand to next area
behave features/pos/ -f rerun -o pos_failures.txt
behave @pos_failures.txt

# Finally, full suite
behave -f rerun -o final_failures.txt
behave @final_failures.txt
```

### CI/CD Integration
```bash
# In CI, capture failures for developer analysis
behave -f rerun -o ci_failures.txt || true
# Upload ci_failures.txt as artifact for developers
```

## Workflow Commands Reference

### Basic Rerun Workflow
```bash
# Capture failures
behave -f rerun -o failed.txt

# Work on failures
behave @failed.txt

# Final confirmation
behave
```

### With KiCad Validation
```bash
# Validation-aware failure capture
JBOM_VALIDATE_KICAD=1 behave -f rerun -o failed.txt

# Focus on failures with enhanced diagnostics
JBOM_VALIDATE_KICAD=1 behave @failed.txt

# Test without validation
behave @failed.txt
```

### Development Phases
```bash
# Phase 1: Identify all issues
JBOM_VALIDATE_KICAD=1 behave -f rerun -o failed.txt

# Phase 2: Fix issues iteratively
JBOM_VALIDATE_KICAD=1 behave @failed.txt

# Phase 3: Confirm fixes without validation overhead
behave @failed.txt

# Phase 4: Full suite confidence check
behave
```

## Benefits

### 1. **Faster Development Cycles**
- Focus only on failing scenarios
- Skip passing tests during development
- Immediate feedback on fixes

### 2. **Better Problem Isolation**
- Clear list of what needs fixing
- No noise from passing tests
- Track progress as list shrinks

### 3. **Efficient Resource Usage**
- Don't waste time on passing tests
- Faster CI/CD feedback loops
- Better development machine performance

### 4. **Integration with Enhanced Diagnostics**
- KiCad validation failures get enhanced diagnostics
- Clear guidance on fixing fake content
- Immediate identification of authenticity issues

### 5. **Scalable Development**
- Works with small and large test suites
- Efficient for teams and CI/CD
- Maintains focus during long development sessions

## File Management

### .gitignore Considerations
```bash
# Add to .gitignore - these are development artifacts
failed_scenarios.txt
*_failures.txt
```

### Multiple Failure Files
```bash
# Different failure types for different development phases
behave -f rerun -o validation_failures.txt  # KiCad validation issues
behave -f rerun -o functional_failures.txt  # Business logic issues
behave -f rerun -o regression_failures.txt  # Regression test issues
```

This workflow dramatically improves development efficiency by focusing effort where it's needed most, while integrating seamlessly with our KiCad validation and enhanced diagnostics system.
