# Issue: Test KiCad Files Don't Match Real KiCad Output

## Problem
The test suite creates "empty" KiCad project files with minimal content that jBOM can parse, but these don't match what KiCad actually generates for empty projects.

## Current Test Implementation
```python
(proj_dir / f"{project_name}.kicad_pro").write_text(
    "(kicad_project (version 1))\n", encoding="utf-8"
)
(proj_dir / f"{project_name}.kicad_sch").write_text(
    "(kicad_sch (version 20211123) (generator eeschema))\n", encoding="utf-8"
)
```

## Issue
This creates files that:
- ✅ **jBOM can read** (minimal parseable content)
- ❌ **Don't match KiCad's actual output** (missing standard sections, metadata, etc.)

## Risk
Tests may pass against artificial files but fail against real KiCad projects due to:
- Missing standard file sections
- Different metadata structure
- Incomplete file headers
- Missing default project settings

## Solution
1. **Capture real KiCad empty project files** as fixtures
2. **Update test project creation** to use authentic KiCad file content
3. **Verify jBOM handles real KiCad files** correctly

## Priority
Medium - Current tests work, but may not catch real-world compatibility issues.

## Context
Discovered during Background abstraction layer design in test suite architecture discussion.
