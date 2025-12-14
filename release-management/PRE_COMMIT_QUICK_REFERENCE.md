# Pre-Commit Hooks - Quick Reference

## Installation

```bash
pre-commit install
```

## Common Commands

### Run hooks on all files
```bash
pre-commit run --all-files
```

### Run a specific hook
```bash
pre-commit run detect-secrets --all-files
pre-commit run black --all-files
pre-commit run flake8 --all-files
```

### Skip hooks (when necessary)
```bash
git commit --no-verify -m "commit message"
```

### Update hook versions
```bash
pre-commit autoupdate
```

## What Each Hook Does

**detect-secrets** - Prevents committing API keys, tokens, passwords (auto-fix: no)
**trailing-whitespace** - Removes trailing spaces (auto-fix: yes)
**end-of-file-fixer** - Adds newline at EOF (auto-fix: yes)
**check-yaml** - Validates YAML syntax (auto-fix: no)
**check-json** - Validates JSON syntax (auto-fix: no)
**check-toml** - Validates TOML syntax (auto-fix: no)
**check-merge-conflicts** - Prevents merge conflict markers (auto-fix: no)
**debug-statements** - Prevents debugger imports like pdb (auto-fix: no)
**mixed-line-ending** - Normalizes line endings to LF (auto-fix: yes)
**black** - Formats Python code (auto-fix: yes)
**flake8** - Enforces PEP 8 style (auto-fix: no)
**bandit** - Security issue scanner (auto-fix: no)

## If a Hook Fails

### Secret detected
1. Remove the secret from the file
2. Use GitHub secrets for API tokens
3. Use environment variables for credentials
4. Commit again

### Code formatting (black)
```bash
black src/
git add src/
git commit -m "chore: format code"
```

### Style violations (flake8)
```bash
flake8 src/  # Show violations
# Fix manually, then commit
```

### Merge conflicts
Search for `<<<<<<<`, `=======`, `>>>>>>>` and resolve before committing.

### False positive (secret detection)
```bash
detect-secrets scan --force-use-all-plugins > .secrets.baseline
git add .secrets.baseline
git commit -m "chore: update secrets baseline

This is a false positive - [explanation]"
```

## Pre-Commit Workflow

```
git commit
  ↓
[Run all hooks]
  ↓
All pass? → Commit successful ✅
  ↓
Hook failed? → Fix issues → git add → git commit (retry)
```

## Documentation

- **Full guide**: [PRE_COMMIT_SETUP.md](PRE_COMMIT_SETUP.md)
- **Security incident**: [SECURITY_INCIDENT_REPORT.md](SECURITY_INCIDENT_REPORT.md)
- **Contributing**: [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md)
