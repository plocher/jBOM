# WARP.md - Agent Development Workflow Guide

This file provides actionable guidance to WARP (warp.dev) agents when working with code in this repository.

You and I are seasoned software developers who understand modern software development practices, architecture, and design. We practice Test-Driven Development (TDD) and Behavior-Driven Development (BDD) using gherkin and behave, maintain good workflow hygiene, and leverage git, GitHub, and automation tools effectively.

When questions arise or choices need to be made among similar alternatives, pause and ask for advice from collaborators.

I will treat you as a trusted collaborator, and I expect to be treated the same way, without fawning or excessive compliments.

## Required Development Workflow

**CRITICAL: All development work MUST follow this A-B-C pattern:**

### A) BEGIN - Feature Branch Creation
- **ALWAYS start by creating a new feature branch** from main:
  ```bash
  git checkout -b feature/issue-N-brief-description
  ```
- Branch name should reference the GitHub issue(s) being addressed
- Examples: `feature/issue-22-fabricator-migration`, `fix/issue-45-cli-help-bug`

### B) PROGRESS - Aggressive Commit Strategy
- **Make frequent commits** as you work through your plan and tasks
- **ALWAYS run git add, pre-commit, and commit after each logical change**
- **Add substantive GitHub issue comments** to document progress, findings, and solutions
- Use semantic commit messages:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `test:` for adding/updating tests
  - `docs:` for documentation changes
  - `refactor:` for code refactoring
- **Include co-author line** in every commit message:
  ```
  Co-Authored-By: Warp <agent@warp.dev>
  ```

### C) FINISH - GitHub PR and Issue Closure
- **Push feature branch** to origin
- **Create GitHub PR** with comprehensive description including:
  - Issues addressed (using "Closes #N" syntax)
  - Changes made with verification steps
  - Architecture impact
  - Testing performed
- **Set PR to close related issues** when merged
- **Record key deliverables** and changes in the PR description

## jBOM Project Context

jBOM is a sophisticated KiCad Bill of Materials generator in Python. It matches schematic components against inventory files (CSV, Excel, Numbers) to produce fabrication-ready BOMs and CPLs with supplier-neutral designs and flexible output customization.

### Project Structure
- **Legacy System**: `~/Dropbox/KiCad/jBOM/src` (READ-ONLY - use for reference and migration)
- **Active Development**: `~/Dropbox/KiCad/jBOM/jbom-new` (ALL changes go here)
- **Architecture**: Domain-centric design with Service-Command pattern
- **Documentation**: `jbom-new/docs/` contains architectural and tutorial knowledge

## Development Practices

### Test-Driven Development
- **BDD**: User-facing behavior using Gherkin scenarios in `./features/`
- **TDD**: Technical unit tests using pytest for implementation correctness
- **Rule**: Feature branch must pass ALL tests before merge to main
- **Process**: Write/update tests FIRST, then implement functionality

### Planning and Execution
- **Use plan + task-based workflow** with explicit review and approval
- **Create implementation plans** using the `create_plan` tool
- **Break down into discrete tasks** using `create_todo_list`
- **Mark tasks complete** as you finish them using `mark_todo_as_done`

### Issue and PR Management
- **Create GitHub Issues** to document problems that won't be immediately addressed
- **Update GitHub Issues** with root-causes, progress, and solutions as context
- **Link PRs to Issues** using "Closes #N" syntax
- **Use conventional commit messages** for semantic versioning

## Environment-Specific Guidance

### Python Environment
- **ALWAYS use**: `PYTHONPATH=/Users/jplocher/Dropbox/KiCad/jBOM/jbom-new/src`
- **Test paths**: Use dot notation (`tests.test_jbom`), not file paths

### Shell (macOS zsh)
- **Quote handling**: Use single quotes for commit messages with `!` (e.g., `'fix!: something'`)
- **Git workflow**: Never work directly in main branch
- **File staging**: Use explicit file lists with `git add`, avoid `git add --all`
- **Pre-commit**: ALWAYS run and fix issues identified. Re-add files after auto-fixes.

### GitHub CLI
- **Issue/PR creation**: Use `--body-file` or JSON representations for complex content
- **Comments**: Use `gh issue comment N --body "text"` for progress updates

## Code Quality Standards

### Architecture Principles
- **Service-Command Pattern**: Services contain business logic, CLI provides thin wrappers
- **Single Responsibility**: Each service has one clear business purpose
- **Domain-Driven Design**: Use electronics domain terminology consistently
- **Configuration-Driven**: Runtime behavior through parameter-based customization

### Code Organization
- **Type hints required** on all functions
- **Docstrings required** for public methods
- **Use dataclasses** for structured data
- **Validation at data intake** points
- **Single responsibility principle** for functions

### Testing Requirements
- **All unit and functional tests must pass** before attempting git commit
- **Behave functional tests MUST pass before opening or merging any PR.**
  - Run from `jbom-new/`: `python -m behave --format progress`
  - Merges are blocked if any scenarios are failed, error, or undefined
  - During development it's fine to run by tag (e.g., `--tags @regression`), but run the full suite before merge
- **Create functional tests** as needed in the `tests/` folder using TDD
- **Update/delete unit tests** proactively as internal design changes
- **Use behave/Gherkin** for user-facing behavior validation

## Test Data and Examples
- **Example inventory files**: `jBOM/examples/example-INVENTORY.{csv,xlsx,numbers}`
- **Sample KiCad projects**: `/Users/jplocher/Dropbox/KiCad/projects/{AltmillSwitches,Core-wt32-eth0,LEDStripDriver}`

## Release Process
1. **Never work directly in main** - always use feature branches
2. **Make semantic commits** with conventional commit messages
3. **Push to feature branch** and create GitHub PR
4. **Check CI/CD pipeline** results and fix any errors
5. **Request review** and wait for approval
6. **Merge when approved** - GitHub Actions handles version bump and PyPI publish

## Critical Reminders

- ✅ **START**: Create feature branch first
- ✅ **PROGRESS**: Commit frequently with issue updates
- ✅ **FINISH**: Create PR that closes issues
- ✅ **TEST**: All tests must pass before merge
- ✅ **COMMUNICATE**: Update issues with progress and findings
- ✅ **DOCUMENT**: Include co-author attribution in commits

This workflow ensures proper tracking, collaboration, and code quality while maintaining project velocity and stakeholder visibility.
