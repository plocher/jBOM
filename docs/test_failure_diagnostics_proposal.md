# Proposal: Improving Behave Test Failure Diagnostics

## Problem Statement

Current test failures provide minimal diagnostic information, making it difficult for developers to understand whether:
1. The test expectations are incorrect
2. The jBOM application behavior is incorrect
3. The test setup or environment is faulty

### Example of Poor Diagnostic Output

```
Scenario: Empty inventory file with header only
  ...
  Then the BOM generation succeeds with exit code 0
    ASSERT FAILED: Expected exit code 0, got 1
```

**Issues:**
- No indication of what command was executed
- No visibility into stdout/stderr output
- No context about what the application actually did
- No information about intermediate state

## Proposed Solution

### 1. Create a Diagnostic Context Helper Module

**File:** `features/steps/diagnostic_utils.py`

```python
"""Diagnostic utilities for test failure reporting."""

from typing import Any, Dict, Optional
import json
from pathlib import Path


def format_execution_context(context, include_files: bool = True) -> str:
    """Format execution context for diagnostic output.

    Args:
        context: Behave context object
        include_files: Whether to include file listing in output

    Returns:
        Formatted diagnostic string
    """
    lines = []
    lines.append("\n" + "=" * 80)
    lines.append("DIAGNOSTIC INFORMATION")
    lines.append("=" * 80)

    # Command executed
    if hasattr(context, 'last_command_output') or hasattr(context, 'cli_command'):
        lines.append("\n--- COMMAND EXECUTED ---")
        if hasattr(context, 'cli_command'):
            lines.append(f"CLI: {context.cli_command}")

    # Exit code
    if hasattr(context, 'last_command_exit_code'):
        lines.append(f"\nExit Code: {context.last_command_exit_code}")

    # Standard output
    if hasattr(context, 'last_command_output'):
        output = context.last_command_output or "(empty)"
        lines.append(f"\n--- STDOUT ---\n{output}")

    # Standard error
    if hasattr(context, 'last_command_error'):
        error = context.last_command_error or "(empty)"
        lines.append(f"\n--- STDERR ---\n{error}")

    # Multi-modal results (CLI, API, Plugin)
    if hasattr(context, 'results'):
        lines.append("\n--- MULTI-MODAL RESULTS ---")
        for method, result in context.results.items():
            lines.append(f"\n{method}:")
            lines.append(f"  Exit Code: {result.get('exit_code', 'N/A')}")
            lines.append(f"  Output: {result.get('output', '(empty)')[:200]}...")
            if 'error_message' in result:
                lines.append(f"  Error: {result.get('error_message', '(empty)')[:200]}...")

    # Working directory
    if hasattr(context, 'scenario_temp_dir'):
        lines.append(f"\n--- WORKING DIRECTORY ---\n{context.scenario_temp_dir}")

    # Files generated
    if include_files and hasattr(context, 'scenario_temp_dir'):
        lines.append("\n--- FILES GENERATED ---")
        try:
            temp_dir = Path(context.scenario_temp_dir)
            if temp_dir.exists():
                files = list(temp_dir.rglob('*'))
                if files:
                    for file in files[:20]:  # Limit to 20 files
                        if file.is_file():
                            size = file.stat().st_size
                            lines.append(f"  {file.name} ({size} bytes)")
                else:
                    lines.append("  (no files generated)")
        except Exception as e:
            lines.append(f"  (error listing files: {e})")

    lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(lines)


def format_comparison(expected: Any, actual: Any, context_label: str = "") -> str:
    """Format expected vs actual comparison.

    Args:
        expected: Expected value
        actual: Actual value
        context_label: Additional context label

    Returns:
        Formatted comparison string
    """
    lines = []
    if context_label:
        lines.append(f"\n{context_label}:")
    lines.append(f"  Expected: {expected}")
    lines.append(f"  Actual:   {actual}")
    return "\n".join(lines)


def assert_with_diagnostics(
    condition: bool,
    message: str,
    context,
    expected: Optional[Any] = None,
    actual: Optional[Any] = None,
) -> None:
    """Assert with enhanced diagnostic output on failure.

    Args:
        condition: Boolean condition to assert
        message: Base assertion message
        context: Behave context object
        expected: Expected value (optional)
        actual: Actual value (optional)

    Raises:
        AssertionError: If condition is False, with diagnostic information
    """
    if not condition:
        diagnostic_parts = [f"\nASSERTION FAILED: {message}"]

        if expected is not None and actual is not None:
            diagnostic_parts.append(format_comparison(expected, actual))

        diagnostic_parts.append(format_execution_context(context))

        raise AssertionError("\n".join(diagnostic_parts))
```

### 2. Update Step Definitions to Use Diagnostic Helpers

**Before (current):**
```python
@then("the BOM generation succeeds with exit code {expected_code:d}")
def step_then_bom_generation_succeeds_with_exit_code(context, expected_code):
    """Verify BOM generation completed with expected exit code."""
    assert hasattr(context, "last_command_exit_code"), "No command was executed"
    actual_code = context.last_command_exit_code
    assert (
        actual_code == expected_code
    ), f"Expected exit code {expected_code}, got {actual_code}"
```

**After (proposed):**
```python
from .diagnostic_utils import assert_with_diagnostics, format_execution_context

@then("the BOM generation succeeds with exit code {expected_code:d}")
def step_then_bom_generation_succeeds_with_exit_code(context, expected_code):
    """Verify BOM generation completed with expected exit code."""

    # Check if command was executed
    if not hasattr(context, "last_command_exit_code"):
        raise AssertionError(
            "No command was executed. Check test setup.\n" +
            format_execution_context(context)
        )

    actual_code = context.last_command_exit_code

    assert_with_diagnostics(
        actual_code == expected_code,
        f"Exit code mismatch",
        context,
        expected=expected_code,
        actual=actual_code,
    )
```

### 3. Enhanced Multi-Modal Result Validation

**Before:**
```python
@then('the error message reports "{expected_message}" and exits with code {exit_code:d}')
def step_then_error_message_reports_and_exits_with_code(
    context, expected_message, exit_code
):
    """Verify error message and exit code across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")
    for method, result in context.results.items():
        assert (
            result["exit_code"] == exit_code
        ), f"{method} wrong exit code: expected {exit_code}, got {result['exit_code']}"
        error_text = result.get("error_message", result.get("output", ""))
        assert (
            expected_message in error_text
        ), f"{method} missing error message: '{expected_message}' not in '{error_text}'"
```

**After:**
```python
from .diagnostic_utils import assert_with_diagnostics, format_execution_context

@then('the error message reports "{expected_message}" and exits with code {exit_code:d}')
def step_then_error_message_reports_and_exits_with_code(
    context, expected_message, exit_code
):
    """Verify error message and exit code across all usage models automatically."""
    context.execute_steps("When I validate error behavior across all usage models")

    failures = []

    for method, result in context.results.items():
        # Check exit code
        actual_exit_code = result.get("exit_code")
        if actual_exit_code != exit_code:
            failures.append(
                f"\n{method} - Exit Code Mismatch:\n"
                f"  Expected: {exit_code}\n"
                f"  Actual:   {actual_exit_code}\n"
                f"  Output:   {result.get('output', '(empty)')[:200]}\n"
                f"  Error:    {result.get('error_message', '(empty)')[:200]}"
            )

        # Check error message
        error_text = result.get("error_message", result.get("output", ""))
        if expected_message not in error_text:
            failures.append(
                f"\n{method} - Missing Error Message:\n"
                f"  Expected substring: '{expected_message}'\n"
                f"  Actual output:      '{error_text[:300]}...'\n"
                f"  Exit code:          {actual_exit_code}"
            )

    if failures:
        diagnostic = (
            "\nMULTI-MODAL VALIDATION FAILURES:\n" +
            "\n".join(failures) +
            format_execution_context(context)
        )
        raise AssertionError(diagnostic)
```

### 4. File Content Validation with Diagnostics

**Before:**
```python
@then("the BOM file contains unmatched components {components}")
def step_then_bom_file_contains_unmatched_components(context, components):
    """Verify the BOM file contains the expected unmatched component references."""
    # Parse component list
    component_refs = [
        comp.strip() for comp in components.replace(" and ", ",").split(",")
    ]

    # Find the output BOM file
    bom_file = None
    for potential_name in ["output.csv", "SimpleProject_BOM.csv", "bom.csv"]:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    assert (
        bom_file and bom_file.exists()
    ), f"BOM output file not found in {context.scenario_temp_dir}"

    # Read BOM file and verify components are present
    with open(bom_file, "r") as f:
        bom_content = f.read()

    for component_ref in component_refs:
        assert (
            component_ref in bom_content
        ), f"Component '{component_ref}' not found in BOM file: {bom_file}"
```

**After:**
```python
from .diagnostic_utils import assert_with_diagnostics, format_execution_context
from pathlib import Path

@then("the BOM file contains unmatched components {components}")
def step_then_bom_file_contains_unmatched_components(context, components):
    """Verify the BOM file contains the expected unmatched component references."""
    # Parse component list
    component_refs = [
        comp.strip() for comp in components.replace(" and ", ",").split(",")
    ]

    # Find the output BOM file
    bom_file = None
    search_names = ["output.csv", "SimpleProject_BOM.csv", "bom.csv"]

    for potential_name in search_names:
        potential_path = context.scenario_temp_dir / potential_name
        if potential_path.exists():
            bom_file = potential_path
            break

    if not bom_file or not bom_file.exists():
        # List all files to help debug
        all_files = list(Path(context.scenario_temp_dir).rglob("*.csv"))
        diagnostic = (
            f"\nBOM file not found!\n"
            f"  Searched for: {', '.join(search_names)}\n"
            f"  In directory: {context.scenario_temp_dir}\n"
            f"  CSV files found: {[f.name for f in all_files] if all_files else '(none)'}\n"
            + format_execution_context(context, include_files=True)
        )
        raise AssertionError(diagnostic)

    # Read BOM file
    with open(bom_file, "r") as f:
        bom_content = f.read()

    # Verify each component
    missing_components = []
    for component_ref in component_refs:
        if component_ref not in bom_content:
            missing_components.append(component_ref)

    if missing_components:
        # Show first 500 chars of BOM for context
        preview = bom_content[:500] + ("..." if len(bom_content) > 500 else "")
        diagnostic = (
            f"\nComponents not found in BOM!\n"
            f"  Missing: {', '.join(missing_components)}\n"
            f"  Expected: {', '.join(component_refs)}\n"
            f"  BOM file: {bom_file}\n"
            f"  BOM preview:\n{preview}\n"
            + format_execution_context(context, include_files=False)
        )
        raise AssertionError(diagnostic)
```

### 5. Warning and Output Validation Enhancement

**Before:**
```python
@then('the output contains warning "{warning_text}"')
def step_then_output_contains_warning(context, warning_text):
    """Verify the command output contains the expected warning message."""
    output = getattr(context, "last_command_output", "") or ""
    error = getattr(context, "last_command_error", "") or ""
    combined_output = f"{output}\n{error}".lower()

    assert (
        warning_text.lower() in combined_output
    ), f"Warning '{warning_text}' not found in output: {combined_output}"
```

**After:**
```python
@then('the output contains warning "{warning_text}"')
def step_then_output_contains_warning(context, warning_text):
    """Verify the command output contains the expected warning message."""
    output = getattr(context, "last_command_output", "") or ""
    error = getattr(context, "last_command_error", "") or ""
    combined_output = f"{output}\n{error}"

    if warning_text.lower() not in combined_output.lower():
        diagnostic = (
            f"\nWarning message not found!\n"
            f"  Expected (case-insensitive): '{warning_text}'\n"
            f"  \n--- ACTUAL STDOUT ---\n{output or '(empty)'}\n"
            f"  \n--- ACTUAL STDERR ---\n{error or '(empty)'}\n"
            + format_execution_context(context, include_files=False)
        )
        raise AssertionError(diagnostic)
```

## Implementation Plan

### Phase 1: Create Diagnostic Utilities (Priority: High)
1. Create `features/steps/diagnostic_utils.py` with helper functions
2. Add unit tests for diagnostic formatting
3. Document usage in testing guidelines

### Phase 2: Update Critical Steps (Priority: High)
Update the most commonly used assertion steps:
1. `step_then_bom_generation_succeeds_with_exit_code` (error_handling/edge_cases.py)
2. `step_then_error_message_reports_and_exits_with_code` (error_handling/edge_cases.py)
3. `step_then_output_contains_warning` (error_handling/edge_cases.py)
4. `step_then_bom_file_contains_unmatched_components` (error_handling/edge_cases.py)

### Phase 3: Systematic Update (Priority: Medium)
Update remaining assertion steps across all feature domains:
- `features/steps/bom/` (15-20 steps)
- `features/steps/pos/` (8-10 steps)
- `features/steps/inventory/` (10-15 steps)
- `features/steps/search/` (5-8 steps)
- `features/steps/annotate/` (5-8 steps)

### Phase 4: Add Context Hooks (Priority: Low)
Add Behave hooks in `features/environment.py` to automatically capture diagnostics:

```python
def after_step(context, step):
    """Capture step execution context for potential failure analysis."""
    if step.status == 'failed':
        # Automatically attach diagnostic info to the step
        if not hasattr(context, '_diagnostic_captured'):
            from features.steps.diagnostic_utils import format_execution_context
            step.error_message += format_execution_context(context)
            context._diagnostic_captured = True
```

## Expected Benefits

### 1. Faster Debugging
- Developers can immediately see what the application actually did
- No need to manually re-run tests to capture output
- Context about the execution environment is readily available

### 2. Better Test Quality
- Easier to identify when test expectations are wrong vs application bugs
- Clear visibility into multi-modal test results (CLI, API, Plugin)
- File system state helps understand test setup issues

### 3. Improved Error Messages
**Current:**
```
ASSERT FAILED: Expected exit code 0, got 1
```

**Proposed:**
```
ASSERTION FAILED: Exit code mismatch
  Expected: 0
  Actual:   1

================================================================================
DIAGNOSTIC INFORMATION
================================================================================

--- COMMAND EXECUTED ---
CLI: jbom bom SimpleProject --inventory empty-inventory.csv --output output.csv

Exit Code: 1

--- STDOUT ---
(empty)

--- STDERR ---
Error: No components found in inventory file: empty-inventory.csv
Consider checking that the file contains valid component data.

--- WORKING DIRECTORY ---
/var/folders/.../jbom_functional_xyz/scenario_Empty_inventory_file/

--- FILES GENERATED ---
  empty-inventory.csv (85 bytes)
  SimpleProject.kicad_pro (52 bytes)
  SimpleProject.kicad_sch (248 bytes)

================================================================================
```

## Risks and Mitigation

### Risk 1: Verbose Output
**Mitigation:** Add environment variable `JBOM_TEST_VERBOSE` to control diagnostic level

### Risk 2: Performance Impact
**Mitigation:** Only format diagnostics when assertions fail (lazy evaluation)

### Risk 3: Breaking Existing Tests
**Mitigation:** Phase implementation, update one module at a time with comprehensive testing

## Alternative Approaches Considered

### Alternative 1: Use pytest with better assertion introspection
**Pros:** pytest provides excellent assertion rewriting
**Cons:** Would require migrating entire test suite from Behave to pytest

### Alternative 2: Custom Behave formatter
**Pros:** Centralized formatting logic
**Cons:** Less flexible, harder to customize per-step

### Alternative 3: Post-failure analysis tool
**Pros:** No changes to step definitions
**Cons:** Requires separate tool, less integrated

## Conclusion

This proposal provides a systematic approach to improving test diagnostics that:
- Maintains compatibility with existing tests
- Provides immediate value with phase 1-2 implementation
- Scales to cover the entire test suite
- Significantly improves developer productivity when debugging test failures

**Recommended Action:** Approve and prioritize implementation of Phases 1-2 for immediate impact.
