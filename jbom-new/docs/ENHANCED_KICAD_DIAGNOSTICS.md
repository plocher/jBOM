# Enhanced KiCad Validation Diagnostics

The KiCad validation framework integrates with jBOM's enhanced diagnostic system to provide comprehensive failure analysis when validation fails.

## Diagnostic Output Structure

When KiCad validation fails, you get a comprehensive diagnostic report:

```
================================================================================
KiCad PROJECT VALIDATION FAILED
================================================================================

Command that would have run: jbom bom
Project directory: /tmp/jbom_behave_xyz

--- VALIDATION ERRORS ---
Project project.kicad_pro: Missing required keys: {'erc', 'libraries'}
Schematic project.kicad_sch: ERC error: Parse error at line 1

--- PROJECT FILE INVENTORY ---
  project.kicad_pro: 26 bytes
    Preview: '(kicad_project (version 1))\n'...
  project.kicad_sch: 45 bytes
    Preview: '(kicad_sch (version 20211123) (genera'...
  No .kicad_pcb files found

--- DETAILED VALIDATION RESULTS ---
Summary: 0/2 files passed

Project Files:
  ❌ FAIL project.kicad_pro: Missing required keys: {'erc', 'libraries', 'cvpcb'}

Schematic Files:
  ❌ FAIL project.kicad_sch: ERC error: Parse error at line 1 (0 violations)

--- KICAD CLI DIAGNOSTICS ---
✅ KiCad CLI found: /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
   Version: KiCad 9.0.0

--- RESOLUTION GUIDANCE ---
• This validation ensures jBOM receives authentic KiCad files, not fake test content
• To disable validation temporarily: unset JBOM_VALIDATE_KICAD
• To fix permanently: replace fake KiCad content with authentic fixtures
• Use scripts/validate_fixtures.py to check all fixtures
• See docs/SEAMLESS_KICAD_VALIDATION.md for integration guide

================================================================================
DIAGNOSTIC INFORMATION
================================================================================

--- COMMAND EXECUTED ---
Command: jbom bom

Exit Code: 1

--- OUTPUT ---
(jBOM output would appear here)

--- WORKING DIRECTORY ---
/tmp/jbom_behave_xyz

================================================================================
END KiCad VALIDATION DIAGNOSTICS
================================================================================
```

## Diagnostic Components

### 1. **Validation Error Summary**
- High-level errors that caused validation to fail
- Per-file breakdown of validation issues
- Clear identification of fake vs authentic content

### 2. **Project File Inventory**
- Complete listing of KiCad files in project directory
- File sizes to identify suspiciously small fake files
- Content previews for small files to show fake content patterns

### 3. **Detailed Validation Results**
- Per-file validation status with pass/fail indicators
- Violation counts from KiCad ERC/DRC tools
- Raw KiCad output for deeper investigation

### 4. **KiCad CLI Diagnostics**
- KiCad CLI availability and version information
- Installation status and path verification
- Version compatibility information

### 5. **Resolution Guidance**
- Step-by-step guidance for fixing validation failures
- Links to relevant documentation and tools
- Temporary workarounds vs permanent fixes

### 6. **Standard Execution Context**
- Integration with jBOM's existing diagnostic system
- Command executed, exit codes, output capture
- Working directory and file system context

## Integration with Existing Diagnostics

The KiCad validation diagnostics seamlessly integrate with your existing `diagnostic_utils.py`:

### Enhanced assert_with_diagnostics()
```python
# In your step definitions, validation failures automatically
# include enhanced diagnostics without code changes

@when('I run jbom command "{args}"')
def step_run_jbom_command(context, args):
    # KiCad validation happens automatically here
    # If validation fails, enhanced diagnostics are generated
    # No changes to your existing step code required
    validate_before_jbom_command(context, args)  # Added automatically
    return original_run_jbom_command(context, args)
```

### Diagnostic Information Layering
1. **KiCad-specific diagnostics** (validation errors, project inventory)
2. **Standard jBOM diagnostics** (command output, execution context)
3. **Behave context** (scenario information, variables)

## Usage Examples

### Development Workflow
```bash
# Enable validation with enhanced diagnostics
export JBOM_VALIDATE_KICAD=1

# Run test that will show enhanced diagnostics on failure
behave features/my_feature.feature

# Example failure output guides you to the fix:
# "Preview: '(kicad_project (version 1))\n'..."  <- Shows fake content
# "Missing required keys: {'erc', 'libraries'}" <- Shows what's missing
```

### Debugging Fake Content
The diagnostics immediately show you the fake content:

```
--- PROJECT FILE INVENTORY ---
  project.kicad_pro: 26 bytes
    Preview: '(kicad_project (version 1))\n'...
```

Compare with authentic content:
```
--- PROJECT FILE INVENTORY ---
  project.kicad_pro: 2847 bytes
    Preview: '{\n  "board": {\n    "3dviewports": [],\n...'
```

### CI/CD Integration
```bash
# In CI pipeline - validation failures include full diagnostics
export JBOM_VALIDATE_KICAD=1
behave --format plain  # Enhanced diagnostics appear in plain format
```

## Diagnostic Control Options

### Environment Variables
- `JBOM_VALIDATE_KICAD=1` - Enable validation with diagnostics
- `JBOM_BEHAVE_TRACE=1` - Enable trace mode for maximum detail

### Scenario Tags
```gherkin
@trace
Scenario: Maximum diagnostic detail
    # Provides extensive file trees and context information

@diagnostic_demo
Scenario: Diagnostic demonstration
    # Used for testing diagnostic output itself
```

### Context Integration
The diagnostics respect your existing context setup:
- Uses `context.sandbox_root` for working directory
- Integrates with `context.last_command` and `context.last_output`
- Works with `context.trace` for enhanced detail

## Error Types and Guidance

### Missing Required Keys
```
Project project.kicad_pro: Missing required keys: {'erc', 'libraries'}

Resolution: Replace fake project file with authentic KiCad fixture
```

### Parse Errors
```
Schematic project.kicad_sch: ERC error: Parse error at line 1

Resolution: Use authentic KiCad schematic format, not minimal text
```

### File Size Indicators
```
project.kicad_pro: 26 bytes  # ← Suspiciously small, likely fake
vs
project.kicad_pro: 2847 bytes  # ← Realistic size for authentic file
```

## Benefits for Development

### 1. **Immediate Problem Identification**
- File inventory shows fake content immediately
- Content previews reveal artificial patterns
- Clear distinction between authentic and fake files

### 2. **Actionable Guidance**
- Specific missing keys identified
- Links to fixture replacement tools
- Clear resolution steps

### 3. **Integration with Workflow**
- Works with existing diagnostic patterns
- No changes to step definitions required
- Respects trace and debugging flags

### 4. **Root Cause Analysis**
- Shows exact validation failures
- Includes KiCad's own error messages
- File-level detail for targeted fixes

This enhanced diagnostic system ensures that when KiCad validation fails, you have all the information needed for quick root cause analysis and resolution, fully integrated with your existing development workflow.
