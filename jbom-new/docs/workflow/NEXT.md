# What to Do Next

## Current Task
**Task 1.2: Extract Value Parsing Utilities** (Ready to start)

**Previous Tasks**:
- ✅ Doc Cleanup (Haiku agent, 13 commits)
- ✅ Task 1.1: Document Anti-Patterns (anti-patterns.md created)

## Current Branch
`feature/phase-1-extract-matcher`

## Context
Starting Phase 1: Extract sophisticated matcher from old-jbom into jbom-new's clean architecture.

Before extracting code, document the architectural problems in old-jbom so we don't repeat them.

This is a structured architectural decision record document that enumerates a list of problems and their resolution:
 * Problem: A succinct problem statement (not a solution statement!) for each identified problem
 * Constraints: Any constraints and requirements that provide context
 * Proposals: A list of potential solutions, each with sufficient architectural level detail for understanding and evaluation
 * Decision: The chosen solution from the above list, with rationale as to why it was chosen
 * Implications: what new architectural commitments and new tech debt/TODOs result from this decision.

## Files to Reference
- `src/jbom/processors/inventory_matcher.py` - mixed responsibilities
- `src/jbom/cli/commands/builtin/bom.py` - CLI coupled to business logic
- `jbom-new/docs/architecture/design-patterns.md` - patterns to follow

## Success Criteria
- File created: `jbom-new/docs/architecture/anti-patterns.md`
- Documents specific examples from old-jbom code
- Explains WHY each is problematic
- Shows what the jbom-new patterns fix each

## Estimated Time
30 minutes

## Notes
This is a learning/analysis task, not code extraction yet.  If there are uncertainties, ambiguities or questions, present the issue to me and ask for input
