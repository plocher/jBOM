# What to Do Next

## Current Task
**Task 1.1: Document Anti-Patterns** (Ready to start)

**Previous Task**: Doc Cleanup ✅ Complete (Haiku agent, 13 commits)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Starting Phase 1: Extract sophisticated matcher from old-jbom into jbom-new's clean architecture.

Before extracting code, document the architectural problems in old-jbom so we don't repeat them.

## Files to Reference
- `src/jbom/processors/inventory_matcher.py` - mixed responsibilities
- `src/jbom/cli/commands/builtin/bom.py` - CLI coupled to business logic
- `jbom-new/docs/architecture/design-patterns.md` - patterns to follow

## Success Criteria
- File created: `jbom-new/docs/architecture/anti-patterns.md`
- Documents specific examples from old-jbom code
- Explains WHY each is problematic
- Shows what jbom-new pattern fixes it

## Estimated Time
30 minutes

## Notes
This is a learning/analysis task, not code extraction yet.
