# Release Management Guidelines

## Semantic Release Automation
- **Version Trigger:** Conventional commits (`fix:`, `feat:`, `chore:`, etc.)
- **Automated Actions:** Version bump, git tag, CHANGELOG.md update, PyPI publish
- **Files Updated:** `pyproject.toml`, `src/jbom/__version__.py`, `CHANGELOG.md`

## Pre-commit Hooks
- Auto-fix formatting, linting, security checks
- Re-add modified files after hook fixes before committing
- Configuration in `pre-commit-setup.md`

## GitHub Secrets Required
- `PYPI_API_TOKEN` - PyPI publishing token
- `GITHUB_TOKEN` - Automatic repository access
- Setup guide in `github-secrets-setup.md`

## Development practices
- Use Test Driven Development for all functionality, creating functional tests as needed in the tests folder
- Create Unit tests for key internal abstractions and functions, deleting or updating them proactively as changes are made to the internal design and implementation
- Use git branches, github PR creation and semantic versioning aware commits for changes
- Update CHANGELOG.md to capture high level changes

## Release Process
1. Make code changes with conventional commit messages
2. Push to main branch
3. GitHub Actions automatically handles version bump and publish
4. No manual releases needed

## Security
- Token rotation procedures in `security-incident-response.md`
- Use `__token__` as username for PyPI authentication
- Never expose tokens in logs or commits
