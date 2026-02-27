# jBOM Developer / Internal Documentation

This directory contains project-internal documentation: architectural decisions,
requirements, design notes, and development workflow guides.

This content is primarily for contributors and AI agents working on the codebase.
For user-facing documentation, see [`docs/`](../README.md).

## Contents

### Architecture
Design principles, architectural decision records (ADRs), and domain model:

- [architecture/README.md](architecture/README.md) — Architecture overview
- [architecture/domain-centric-design.md](architecture/domain-centric-design.md) — Domain model and design rationale
- [architecture/why-jbom-new.md](architecture/why-jbom-new.md) — v7 refactoring summary
- [architecture/design-patterns.md](architecture/design-patterns.md) — Patterns and anti-patterns
- [architecture/layer-responsibilities.md](architecture/layer-responsibilities.md) — Layer boundaries
- [architecture/adr/](architecture/adr/) — Architectural Decision Records

### Requirements
User scenarios and functional specifications:

- [requirements/0-User-Scenarios.md](requirements/0-User-Scenarios.md) — User-facing scenarios
- [requirements/1-Functional-Scenarios.md](requirements/1-Functional-Scenarios.md) — Functional requirements

### Development Notes
Active design notes and investigation results:

- [development_notes/active/](development_notes/active/) — Active requirements and investigations
- [development_notes/completed/](development_notes/completed/) — Completed design work
- [development_notes/BDD_AXIOMS.md](development_notes/BDD_AXIOMS.md) — BDD writing guidelines
- [development_notes/development_tasks.md](development_notes/development_tasks.md) — Task tracking

### Guides
Developer and workflow guides:

- [guides/DEVELOPER_GUIDE.md](guides/DEVELOPER_GUIDE.md) — Architecture and implementation guide
- [guides/USER_GUIDE.md](guides/USER_GUIDE.md) — User workflow guide (broader than man pages)

### Workflow
Git workflow, session notes, and priorities:

- [workflow/NEXT.md](workflow/NEXT.md) — Current priorities
- [workflow/GIT_WORKFLOW.md](workflow/GIT_WORKFLOW.md) — Branching and commit conventions
- [workflow/WORK_LOG.md](workflow/WORK_LOG.md) — Session notes
- [workflow/QUICK_START.md](workflow/QUICK_START.md) — Quick reference for paired development
