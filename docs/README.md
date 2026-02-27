# jBOM Documentation

## User Documentation

These are the primary references for users and integrators:

| File | Contents |
|------|----------|
| [README.man1.md](README.man1.md) | CLI reference — all 6 commands, flags, examples |
| [README.man3.md](README.man3.md) | Python API — planned interface for programmatic use |
| [README.man4.md](README.man4.md) | KiCad Eeschema plugin setup and usage |
| [README.man5.md](README.man5.md) | Inventory file format — columns, matching behavior |
| [README.developer.md](README.developer.md) | Developer deep-dive — architecture, extension points |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute — setup, workflow, tests |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## Developer / Internal Documentation

Content in [`docs/dev/`](dev/) is internal to the project:

- **[dev/architecture/](dev/architecture/)** — Design principles, ADRs, domain model
- **[dev/requirements/](dev/requirements/)** — User scenarios and functional specifications
- **[dev/development_notes/](dev/development_notes/)** — Active and completed design notes
- **[dev/guides/](dev/guides/)** — Developer and user workflow guides
- **[dev/workflow/](dev/workflow/)** — Git workflow, work logs, next steps

## Quick Reference

Install and generate a BOM:
```bash
pip install jbom
jbom bom MyProject/ --inventory inventory.csv -o bom.csv --jlc
```

See [../README.md](../README.md) for the full quick-start guide.
