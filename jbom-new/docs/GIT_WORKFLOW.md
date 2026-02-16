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

When I ask you to commit, use this pattern:

```bash
# 1. Stage new/modified files
# Since git add -A adds all the things, it a rather heavy-handed command: we don't want to
# blindly add untracked files, since we create working temp files that shouldn't end up in the repo.
# If we can't provide an explicit list of the files we have been modifying, we restrict ourselves
# to using `git add -u` to skip untracked files and only add tracked files.

git add specific files   # or
git add -u               # for all tracked files

# 2. Run pre-commit (may fail due to fixes or found problems)
pre-commit
# This WILL fail if pre-commit makes changes or finds issues

# 3. Read the pre-commit output looking for failures and error messages that need to be addressed
# such as issues with imports (etc) that it can't auto-fix.
# Fix all the issues it reports, re-add fixed files and re-run pre-ommit
git add -u
pre-commit

# 4. Continue this pre-commit loop until pre-commit runs cleanly.
# Once pre-commit gives a clean bill of health, commit
git commit -m "type: description

Details."
```

### Git Commit Anti-patterns (NOT Recommended)

On the surface, these snippets feel like a great optimization, until you realize that the commit will usually fail due to pre-commit hooks finding something to gripe about.
The Marines have a saying: slow is smooth, smooth is fast.  This isn't smooth.

```bash
# Stage changes and commit in one go, handling pre-commit fixes
git add [files] && \
git commit -m "message" || \
(git add -u && git commit -m "message")
```
or

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

These hooks **only check** (but don't modify) the files.  Issues they identify MUST be fixed by the agent or human before the commit will be allowed.

- `check yaml/json/toml` - Validates syntax
- `check for merge conflicts` - Looks for conflict markers
- `black/flake8/bandit` - Python linting (if Python files)

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
"
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
"
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
"
```

## Troubleshooting

### Commit Keeps Failing

```bash
# See what pre-commit is complaining about and address the problems it calls out.
# `git commit` implicitly runs pre-commit and will fail if pre-commit fails.
pre-commit

# Check what pre-commit changed
git diff

# If changes look good, re-add
git add -u
# RE RUN pre-commit to verify everything is good
pre-commit
git add -u
git commit -m "your real message"
```

### Pre-Commit Made Unwanted Changes

```bash
# Revert pre-commit changes
git checkout -- [file]

# Skip pre-commit (always ask me before doing this!)
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
✅ **Use semantic commit types** (feat, fix, docs, test, refactor)
✅ **Write descriptive messages** - what changed and why

❌ **Don't use `--no-verify`** unless I explicitly tell you to
❌ **Don't fight pre-commit** - it's there to help
❌ **Don't commit without testing** - run tests first
