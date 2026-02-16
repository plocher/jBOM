# Git Workflow with Pre-Commit Hooks

## Feature Branch Workflow

### Always Work in Feature Branches

**Rule**: NEVER work directly in `main`. Always create a feature branch first.

```bash
# Create and switch to feature branch
git checkout -b feature/phase-N-description

# Or if branch exists
git checkout feature/phase-N-description
```

**Branch naming convention**:
- `feature/phase-1-extract-matcher` - Phase-based work
- `feature/issue-48-sophisticated-matching` - Issue-based work
- `fix/issue-50-field-names` - Bug fixes

### When to Create Feature Branch

✅ **Before starting any Phase work**
✅ **Before addressing any GitHub issue**
✅ **For any non-trivial changes**

❌ **Never commit directly to main**

### Merging Feature Branch

When Phase 1 is complete:
1. Push feature branch: `git push -u origin feature/phase-1-extract-matcher`
2. Create GitHub PR
3. Wait for CI/CD checks
4. Merge PR when approved

## Pre-Commit Hook Workflow

### The Problem

Pre-commit hooks **modify files** when they run (fixing trailing whitespace, line endings, etc.). If you commit without re-adding, the commit fails because files changed after staging.

## The Correct Pattern

### For Agent Sessions

```bash
# 1. Stage your changes
git add [files]

# 2. Run pre-commit manually to see what needs fixing
git commit -m "your message"
# This WILL fail if pre-commit makes changes

# 3. Pre-commit modified files - re-add them
git add -u  # Add all tracked files that were modified

# 4. Commit again with same message
git commit -m "your message"
# This should succeed
```

### Quick Version (Recommended)

```bash
# Stage changes and commit in one go, handling pre-commit fixes
git add [files] && \
git commit -m "message" || \
(git add -u && git commit -m "message")
```

This:
1. Stages your files
2. Tries to commit
3. If pre-commit modifies files (fails), re-adds all updated files
4. Commits again

### Even Simpler (For Agent Use)

```bash
# Let pre-commit do its thing, then commit everything
git add [new files]
git add -u  # Stage all tracked file updates
git commit -m "message"
```

## Common Pre-Commit Fixes

These hooks **automatically modify** files:

- `trailing-whitespace` - Removes trailing spaces
- `fix end of file` - Ensures newline at EOF
- `fix mixed line endings` - Normalizes CRLF/LF

These hooks **only check** (don't modify):

- `check yaml/json/toml` - Validates syntax
- `check for merge conflicts` - Looks for conflict markers
- `black/flake8/bandit` - Python linting (if Python files)

## For Agents: Standard Commit Pattern

When I ask you to commit, use this pattern:

```bash
# 1. Stage new/modified files
git add [specific files or -A for all]

# 2. Commit (may fail due to pre-commit fixes)
git commit -m "type: description

Details about what changed.

Co-Authored-By: Warp <agent@warp.dev>"

# 3. If that failed, re-add fixed files and commit
git add -u
git commit -m "type: description

Details about what changed.

Co-Authored-By: Warp <agent@warp.dev>"
```

Or combined:

```bash
git add [files] && \
git add -u && \
git commit -m "type: description

Details.

Co-Authored-By: Warp <agent@warp.dev>"
```

## Semantic Commit Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `refactor:` - Code change that neither fixes bug nor adds feature
- `test:` - Adding or updating tests
- `chore:` - Maintenance (dependencies, config, etc.)

## Examples

### Documentation Commit

```bash
git add jbom-new/docs/architecture/anti-patterns.md
git add -u
git commit -m "docs: document anti-patterns from old-jbom

Identifies 5 architectural problems:
- Mixed responsibilities in InventoryMatcher
- Constructor doing I/O
- CLI concerns in business logic
- Tight coupling between services
- Debug printing in domain layer

Each with code examples and jbom-new alternatives.

Co-Authored-By: Warp <agent@warp.dev>"
```

### Feature Commit

```bash
git add jbom-new/src/jbom/common/value_parsing.py
git add -u
git commit -m "feat: add value parsing utilities

Port from old-jbom with type hints and docstrings:
- parse_res_to_ohms() - Resistor value parsing
- parse_cap_to_farad() - Capacitor value parsing
- parse_ind_to_henry() - Inductor value parsing
- EIA standard converters

Pure functions, no side effects, ready for use in matcher.

Co-Authored-By: Warp <agent@warp.dev>"
```

### Test Commit

```bash
git add jbom-new/tests/unit/test_value_parsing.py
git add -u
git commit -m "test: add unit tests for value parsing

Coverage for all parsing functions:
- Resistor: 10K, 2M2, 0R22 formats
- Capacitor: 100nF, 1u0, 220pF formats
- Inductor: 10uH, 2m2 formats
- Edge cases: empty strings, malformed input

All tests passing, 85% coverage.

Co-Authored-By: Warp <agent@warp.dev>"
```

## Troubleshooting

### Commit Keeps Failing

```bash
# See what pre-commit is complaining about
git commit -m "test"

# Check what pre-commit changed
git diff

# If changes look good, re-add
git add -u
git commit -m "your real message"
```

### Pre-Commit Made Unwanted Changes

```bash
# Revert pre-commit changes
git checkout -- [file]

# Skip pre-commit (use sparingly!)
git commit --no-verify -m "message"
```

### Want to See Pre-Commit Output

```bash
# Run pre-commit manually before commit
pre-commit run --all-files

# Or just on staged files
pre-commit run
```

## Remember

✅ **Always use `git add -u`** after first commit attempt
✅ **Include Co-Authored-By line** in commit messages
✅ **Use semantic commit types** (feat, fix, docs, test, refactor)
✅ **Write descriptive messages** - what changed and why

❌ **Don't use `--no-verify`** unless absolutely necessary
❌ **Don't fight pre-commit** - it's there to help
❌ **Don't commit without testing** - run tests first
