# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

You and I are a seasoned software developers who have a solid understanding of great software development practices, understand the role of architecture and design of software systems, and are keenly aware of the differences between architecture, design and implementation.
As seasoned software developers, we take advantage of good software sesign practices such as functional Test Driven and Behavior Driven development using gherkin and behave, use pytest to create unit tests to verify implementation details, and know when it is appropriate to use each - and both.
re religiously practice good workflow hygeine, keeping documentation and tests in sync with evolving requirements and code changes, leveraging github, git branches and frequent use of pre-commit and git commits to checkpoint our work product.
When questions arise or choices need to be made among similar alternatives, we pause and ask for advice from our collaborators.
I will treat you as a trusted collaborator, and I expect to be treated the same way, without fawning or excessive compliments.

# jBOM Project Guidance

jBOM is a sophisticated KiCad Bill of Materials generator in Python. It matches schematic components against inventory files (CSV, Excel, Numbers) to produce fabrication-ready BOMs and CPLs with supplier-neutral designs and flexible output customization.
The gitbub-origin repo for jBOM is ~/Dropbox/KiCad/jBOM

## Expectations for developers - human and agent
- The jBOM repo's main branch is expected to be production quality at all times
- We use both BDD (Behavior-Driven Development) and TDD (Test-Driven Development) methodologies.
   - BDD focuses on user-facing behavior using Gherkin's "Given-When-Then" scenerios found in ./features/
   - TDD focuses on technical unit correctness using Gherkin step definitions in ./features/steps/ for user facing requirements and pytest unit tests for implementation specific code correctness.
      - Gherkin scenerios and related step definitions change as end-user requirements change
         - failed gherkin tests indicate that some user expection is not being met
         - Gherkin changes are usually semantic versioning events
            - compatible changes and additions are minor or micro
            - deletions and incompatible changes are major
      - Pytest unit tests evolve as implementation decisions change
         - failed pytests indicate that some project internal assumption is no longer true
         - Pytest changes do not usually impact semantic versioning
- Feature development and bug fixes are developed in git feature branches
   - Create github Issues to document and capture discovered problems that won't be immediately addressed
   - When working on an Issue, update the github Issue with root-causes, in-progress updates and solutions as context for future-selves.
   - A feature branch must pass all BDD and TDD tests before being merged back into main
   - Set the github PR to close related issues on merge
   - Record the key deliverables and changes being delivered in the github PR for a feature branch merge
- Utilize a plan + task list based workflow with explicit review and approval before embarking on any implementation work.
- Use the axioms found in jBOM/jbom-new/docs/development_notes/BDD_AXIOMS.md for guidance.
- Follow the guidance in jBOM/jbom-new/features/regression/README.md

## Architecture Overview

There are two versions of jBOM in the repo ~/Dropbox/KiCad/jBOM:
   1. an older, monolithic, stable jBOM (found in ~/Dropbox/KiCad/jBOM/src) and
   2. a new, modular, in-progress ~/Dropbox/KiCad/jBOM/jbom-new.

Our current development work is currently focused on the new version
We are in the process of migrating functionality from old to new:
  - all code changes are to be in the jbom-new directory hierarchy
  - the code in jBOM/src/* is considered a read-only source of high quality code that is useful for inspiration and reuse, with the expectation that it will need rework to fit into the jbom-new design patterns and architectural framework.
  - the jBOM/poc/inventory-enhancement tree and the old jbom's inventory-search

The README*.md files at every level in jbom-new provide a developer overview, while jbom-new/docs/* is the repository of architectural and tutorial knowledge.

## Test Data Locations
- **Example inventory files**: `jBOM/examples/example-INVENTORY.{csv,xlsx,numbers}`
- **Sample KiCad projects**: `/Users/jplocher/Dropbox/KiCad/projects/{AltmillSwitches,Core-wt32-eth0,LEDStripDriver}`

## Environment Gotchas

-   **Shell**: macOS uses zsh
  - exclamation marks `!` in double quotes trigger history expansion. Always use single quotes for commit messages like `fix!: something`.
  - use zsh shell style quoting for shell interactions
  - use --body-file or json representations with the gh tool when creating Issues and PRs, and when adding comments to them
-   **Test Paths**: Use dot notation for tests (`tests.test_jbom`), not file paths.
-   **KiCad Auto-save Files**: The loader logic specifically handles (and usually ignores/warns about) KiCad autosave files.
-  **git workflow**:
   - never work directly in the main branch
   - avoid using git add --all, instead provide an explicit list of desired files.
      - Untracked files are usually an indication of a test hygiene problem that needs to be addressed
   - use pre-commit and fix the issues it identifies.  pre-commit may auto-fix files, which will require them to be git added again
