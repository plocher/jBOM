# WARP.md - Agent Development Workflow Guide

This file provides actionable guidance to WARP (warp.dev) agents when working with code in this repository.

You and I are seasoned software developers who understand modern software development practices, architecture, and design. We practice Test-Driven Development (TDD) and Behavior-Driven Development (BDD) using gherkin and behave, maintain good workflow hygiene, and leverage git, GitHub, and automation tools effectively.

When questions arise or choices need to be made among similar alternatives, pause and ask for advice from collaborators.

I will treat you as a trusted collaborator, and I expect to be treated the same way, without fawning or excessive compliments.

## Required Development Workflow

Follow the **`git-workflow`** project skill
(`.agents/skills/git-workflow/SKILL.md`) for the feature-branch +
iterative-pre-commit + semantic-commit + PR-creation procedure.

Key constraints (rules, not procedure):
- **Never commit directly to `main`.** All work happens in a feature branch.
- **Branch names reference the GitHub issue(s) being addressed**:
  `feature/issue-N-brief-description`, `fix/issue-N-brief-description`.
- **After a PR merge, run scripted branch cleanup** with
  `python scripts/post_merge_cleanup.py --branch <branch-name>` before
  considering the workflow complete.
- **Add substantive GitHub issue comments** to document progress,
  findings, and solutions as work proceeds.
- **All tests must pass before a PR can merge** — see `Testing
  Requirements` below.

## jBOM Project Context

jBOM is a sophisticated KiCad Bill of Materials generator in Python. It matches schematic components against inventory files (CSV, Excel, Numbers) to produce fabrication-ready BOMs and CPLs with supplier-neutral designs and flexible output customization.

### Project Structure
- **Active source**: `~/Dropbox/KiCad/jBOM/src/jbom/`
- **Tests**: `~/Dropbox/KiCad/jBOM/tests/` (pytest) and `~/Dropbox/KiCad/jBOM/features/` (behave/BDD)
- **Architecture**: Domain-centric design; service / command / application layering (see `docs/architecture/adr/`).
- **Documentation**: `~/Dropbox/KiCad/jBOM/docs/` — governed by `docs/README.md` (the documentation charter).

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
- **ALWAYS use**: `PYTHONPATH=/Users/jplocher/Dropbox/KiCad/jBOM/src`
- **Test paths**: Use dot notation (`tests.test_jbom`), not file paths

### Shell + git + GitHub CLI procedure

Procedural guidance for staging, commits, pre-commit handling, zsh
quoting of conventional-commit messages, and `gh` issue/PR authoring
lives in the `git-workflow` skill at
`.agents/skills/git-workflow/SKILL.md`. Follow that skill rather than
duplicating the steps here. This includes mandatory post-merge
patch-equivalence cleanup via `scripts/post_merge_cleanup.py`.

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
- **Unit and functional tests for an item should pass** before they are committed
- **Behave functional tests MUST pass before opening or merging any PR.**
  - Run from `repo root`: `python -m behave --format progress`
  - Merges are blocked if any scenarios are failed, error, or undefined
  - During development it's fine to run by tag (e.g., `--tags @regression`), but run the full suite before merge
- **Create functional tests** as needed in the `tests/` folder using TDD
- **Update/delete unit tests** proactively as internal design changes
- **Use behave/Gherkin** for user-facing behavior validation

## Test Data and Examples
- **Example inventory files**: `jBOM/examples/example-INVENTORY.{csv,xlsx,numbers}`
- **Sample KiCad projects**: `/Users/jplocher/Dropbox/KiCad/projects/{AltmillSwitches,Core-wt32-eth0,LEDStripDriver}`

## Release Process

Releases are automated by semantic-release on merge to `main`. The
developer-facing procedure (feature branch → commits → PR → merge)
is covered by the `git-workflow` skill. The automation itself (the
CHANGELOG generator, pre-commit hook, and CI staleness check) is
tracked by #305.

## Critical Reminders

- ✅ **START**: Create feature branch first
- ✅ **PROGRESS**: Commit frequently with issue updates
- ✅ **FINISH**: Create PR that closes issues
- ✅ **TEST**: All tests must pass before merge
- ✅ **COMMUNICATE**: Update issues with progress and findings
- ✅ **DOCUMENT**: Include co-author attribution in commits

This workflow ensures proper tracking, collaboration, and code quality while maintaining project velocity and stakeholder visibility.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for this repository (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default canonical label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Domain docs are single-context: root `CONTEXT.md` (when present) and ADRs in `docs/architecture/adr/`. See `docs/agents/domain.md`.
