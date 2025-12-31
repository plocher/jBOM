# Systematic Solution for Behave Step Loading Conflicts

## Problem Summary

The jBOM project had behave step loading conflicts where step definitions in subdirectories were not being discovered properly, resulting in:
- Import errors with `KeyError: "'__name__' not in globals"`
- Undefined step errors despite step definitions existing
- AmbiguousStep conflicts between similar step patterns

## Root Causes Identified

1. **Relative Import Issues**: Behave executes step files using `exec()` without providing `__name__` in globals, making relative imports (`from . import`) fail
2. **Complex Import Logic**: The original `pkgutil.walk_packages` approach didn't work reliably with behave's execution model
3. **Step Conflicts**: Some steps had overlapping patterns causing AmbiguousStep errors

## Systematic Solution Applied

### Phase 1: Simplified Import Strategy
- **Removed complex import logic**: Replaced `pkgutil.walk_packages` with empty `__init__.py`
- **Let behave handle discovery**: Behave automatically discovers `.py` files in subdirectories when `__init__.py` exists
- **Eliminated relative imports**: Avoided problematic `from . import` statements

### Phase 2: Resolved Step Conflicts
- **Identified AmbiguousStep issues**: Found conflicting step patterns between generic and specific steps
- **Removed duplicate steps**: Eliminated steps that conflicted with existing parameterized patterns
- **Fixed missing dependency steps**: Added missing `"When I validate annotation across all usage models"` step

### Phase 3: Validated Solution
- **Import errors resolved**: No more `KeyError: "'__name__' not in globals"` errors
- **AmbiguousStep conflicts eliminated**: No more step definition conflicts
- **Significant reduction in undefined steps**: From major import failures to only specific missing implementations

## Current Structure

```
features/
├── steps/
│   ├── __init__.py         # Empty - lets behave discover subdirectories
│   ├── shared.py          # Cross-domain shared steps
│   ├── annotate/
│   │   ├── __init__.py    # Contains step imports for subdirectory
│   │   └── back_annotation.py
│   ├── bom/
│   │   ├── __init__.py    # Contains step imports for subdirectory
│   │   ├── component_matching.py
│   │   ├── fabricator_formats.py
│   │   └── shared.py      # Domain-specific shared steps
│   └── [other domains...]
```

## Key Principles for Future Maintenance

1. **Keep main `__init__.py` empty**: Avoid complex import logic that conflicts with behave
2. **Use absolute imports where needed**: Avoid relative imports in step definition files
3. **Let behave discover naturally**: Trust behave's built-in step discovery mechanism
4. **Test systematically**: Use `behave --dry-run` to validate step loading before implementation

## Remaining Work

- Some undefined steps still exist (these are implementation TODOs, not loading issues)
- Step matching patterns may need refinement for specific use cases
- Additional missing steps need implementation

## Success Metrics

- ✅ No more import errors
- ✅ No more AmbiguousStep conflicts
- ✅ Behave successfully discovers step files in subdirectories
- ✅ Organized, maintainable structure preserved
- ✅ Systematic approach documented for future extensions

## References

- [QC Analytics Blog Post](https://qc-analytics.com/2019/10/importing-behave-python-steps-from-subdirectories/) - Original inspiration
- [Behave Issue #742](https://github.com/behave/behave/issues/742) - Related import issues
- Behave's step discovery mechanism relies on `__init__.py` files to treat directories as packages
