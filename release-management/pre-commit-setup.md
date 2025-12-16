# Pre-Commit Hooks Setup Guide

This guide explains the pre-commit hooks configured for jBOM to maintain code standards and quality (no secret scanner is used).

## What Are Pre-Commit Hooks?

Pre-commit hooks are scripts that run automatically before you commit code. They can:
- Fix code formatting issues
- Validate file syntax
- Enforce code quality standards
- Prevent debug statements from being committed

## Installation

Pre-commit hooks are already installed when you cloned the repository. They run automatically on `git commit`.

### Manual Installation (if needed)

```bash
pip install pre-commit
pre-commit install
```

### Verify Installation

```bash
ls -la .git/hooks/pre-commit
# Should show the pre-commit hook file
```

## What Hooks Are Running?


### 2. **Trailing Whitespace**

Removes extra spaces at end of lines

### 3. **End of File Fixer**

Ensures all files end with a newline

### 4. **YAML/JSON/TOML Validators**

Checks syntax of configuration files

### 5. **Merge Conflict Detector**

Prevents committing merge conflict markers (`<<<<<<<`, `=======`, etc.)

### 6. **Debug Statement Detector**

Prevents committing Python debugger imports (`pdb`, `ipdb`, etc.)

### 7. **Line Ending Normalizer**

Converts CRLF (Windows) to LF (Unix) line endings

### 8. **Black Code Formatter**

Auto-formats Python code to consistent style

### 9. **Flake8 Linter**

Enforces Python style guide (PEP 8)

### 9. **Bandit Security Scanner**

Detects common security issues in Python code

## Workflow When Committing

### Successful Commit

```bash
$ git commit -m "feat: add new feature"
trim trailing whitespace.................................................Passed
fix end of file.........................................................Passed
check yaml.............................................................Passed
check json.............................................................Passed
check toml.............................................................Passed
check for merge conflicts................................................Passed
check for debugger imports...............................................Passed
fix mixed line endings...................................................Passed
format with black........................................................Passed
flake8..................................................................Passed
bandit..................................................................Passed

[main a1b2c3d] feat: add new feature
```


```bash
$ git commit -m "add pypi token"

Detect secrets scan......................FAILED

Secret 'pypi-' found in GITHUB_SECRETS_SETUP.md

Fix the file by removing the secret, then try again.
```

**Action**: Remove the secret, then commit again.

### Failed Commit (Code Issues)

```bash
$ git commit -m "fix: formatting"

black..................................................................Failed
error: cannot format src/module.py: Cannot parse: 1:0:
```

**Action**: Fix the syntax error, then commit again.


If you need to skip hooks for a commit (not recommended):

```bash
git commit --no-verify -m "Skip hooks message"
```

⚠️ Use sparingly - you're bypassing important checks!

## Configuration

The `.pre-commit-config.yaml` file controls which hooks run. To modify:

1. Edit `.pre-commit-config.yaml`
2. Run: `pre-commit install-hooks`
3. Test with: `pre-commit run --all-files`

## Testing Hooks

### Run Hooks on All Files

```bash
pre-commit run --all-files
```

### Run Specific Hook

```bash
pre-commit run detect-secrets --all-files
pre-commit run black --all-files
```

### Test Secret Detection

```bash
# This should fail (contains fake token)
echo "pypi-AgEIcHlwaS5vcmc" > test.py
pre-commit run detect-secrets --files test.py

# Clean up
rm test.py
```

## Common Issues

### "Hook failed: detect-secrets"

**Problem**: A secret was detected

**Solution**:
1. Inspect the file mentioned
2. Remove any sensitive information
3. Commit again

### "Hook failed: black"

**Problem**: Code formatting issues

**Solution**:
```bash
black src/
git add src/
git commit -m "chore: format code with black"
```

### "Hook failed: flake8"

**Problem**: Code style violations

**Solution**: Fix the violations manually or:
```bash
# Show violations
flake8 src/

# Fix what you can
autopep8 --in-place src/file.py
```

### Hooks Not Running

**Problem**: You modified `.git/hooks/pre-commit` directly

**Solution**:
```bash
pre-commit uninstall
pre-commit install
```

## Files Related to Pre-Commit

- `.pre-commit-config.yaml` - Configuration for all hooks
- `.git/hooks/pre-commit` - Installed hook (auto-generated)

## Security Best Practices

1. ✅ **Always let hooks run** before committing
2. ✅ **Never commit secrets** even accidentally
3. ✅ **Use GitHub secrets** for API tokens
4. ✅ **Use environment variables** for credentials
5. ✅ **Don't commit fake tokens** in examples (use placeholders instead)
6. ✅ Enable GitHub Secret Scanning in repo settings

## Updating Hooks

Pre-commit.ci automatically updates hooks weekly. To update manually:

```bash
pre-commit autoupdate
```

## Reference

- Pre-commit docs: https://pre-commit.com/
- detect-secrets: https://github.com/Yelp/detect-secrets
- Black formatter: https://black.readthedocs.io/
- Flake8: https://flake8.pycqa.org/
- Bandit: https://bandit.readthedocs.io/
