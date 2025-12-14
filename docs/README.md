# jBOM Development & Release Documentation

This directory contains development, release management, and architectural documentation for the jBOM project. These files are excluded from the PyPI package distribution.

## Contents

### Developer Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Contribution guidelines, development setup, testing procedures, and code style standards
- **[README.developer.md](README.developer.md)** — Technical architecture, core classes, key algorithms, and implementation details
- **[README.tests.md](README.tests.md)** — Test suite organization, testing guidelines, and test case documentation

### Release & CI/CD Management

- **[CHANGELOG.md](CHANGELOG.md)** — Version history and release notes
- **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** — GitHub secrets and variables configuration guide for CI/CD workflows
- **[README.developer.md](README.developer.md)** — Includes automated release process documentation using semantic versioning

### Security & Code Quality

- **[SECURITY_INCIDENT_REPORT.md](SECURITY_INCIDENT_REPORT.md)** — Documentation of the PyPI token exposure incident, remediation steps, and prevention measures
- **[PRE_COMMIT_SETUP.md](PRE_COMMIT_SETUP.md)** — Comprehensive guide to pre-commit hooks for secret detection and code quality
- **[PRE_COMMIT_QUICK_REFERENCE.md](PRE_COMMIT_QUICK_REFERENCE.md)** — Quick lookup reference for common pre-commit operations

### Architecture & Design

- **[WARP.md](WARP.md)** — Warp development environment notes and architectural guidance

## PyPI Package Contents

These documentation files are **not included** in the PyPI distribution. The PyPI package contains:

- **User-facing documentation:**
  - `README.md` — Overview and quick start
  - `README.man1.md` — CLI reference
  - `README.man3.md` — Python API reference
  - `README.man4.md` — KiCad plugin setup
  - `README.man5.md` — Inventory file format

- **Core files:**
  - Source code in `src/jbom/`
  - Test suite in `tests/`
  - License file

## For Contributors

1. Start with **[CONTRIBUTING.md](CONTRIBUTING.md)** for development setup
2. Review **[README.developer.md](README.developer.md)** for architecture
3. Check **[PRE_COMMIT_QUICK_REFERENCE.md](PRE_COMMIT_QUICK_REFERENCE.md)** before committing
4. See **[GITHUB_SECRETS_SETUP.md](GITHUB_SECRETS_SETUP.md)** if you need to set up CI/CD

## For Maintainers

- Release process: See "Automated Releases with Semantic Versioning" section in [README.developer.md](README.developer.md)
- Security incidents: Follow procedures in [SECURITY_INCIDENT_REPORT.md](SECURITY_INCIDENT_REPORT.md)
- Pre-commit hooks: Use [PRE_COMMIT_QUICK_REFERENCE.md](PRE_COMMIT_QUICK_REFERENCE.md) for common operations
