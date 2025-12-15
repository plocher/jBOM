# Release Management Guidelines

## Semantic Release Automation
- **Version Trigger:** Conventional commits (`fix:`, `feat:`, `chore:`, etc.)
- **Automated Actions:** Version bump, git tag, CHANGELOG.md update, PyPI publish
- **Files Updated:** `pyproject.toml`, `src/jbom/__version__.py`, `CHANGELOG.md`

## Pre-commit Hooks
- Auto-fix formatting, linting, security checks
- Re-add modified files after hook fixes before committing
- Configuration in `PRE_COMMIT_SETUP.md`

## GitHub Secrets Required
- `PYPI_API_TOKEN` - PyPI publishing token
- `GITHUB_TOKEN` - Automatic repository access
- Setup guide in `GITHUB_SECRETS_SETUP.md`

## Release Process
1. Make code changes with conventional commit messages
2. Push to main branch
3. GitHub Actions automatically handles version bump and publish
4. No manual releases needed

## Security
- Token rotation procedures in `SECURITY_INCIDENT_REPORT.md`
- Use `__token__` as username for PyPI authentication
- Never expose tokens in logs or commits
