# Bootstrap Progress - Step 1

## Goal
Build minimal viable core: CLI basics + plugin discovery infrastructure

## Features (in order)
1. `features/cli_basics.feature` - Basic CLI (--help, --version, error handling)
2. `features/plugin_discovery.feature` - Core plugin discovery and listing

## Success Criteria
- [ ] CLI responds to --help and --version
- [ ] CLI handles unknown commands gracefully
- [ ] Plugin discovery scans src/jbom_new/plugins/
- [ ] Service and workflow registries built at startup
- [ ] `jbom plugins list` shows discovered plugins

## Note
Directory is `jbom-new/` but command remains `jbom` to avoid tech debt.

## Not in Step 1
- KiCad reading (moved to future/)
- BOM generation (moved to future/)
- Plugin installation (that's Step 4)
- Configuration system (that's Step 3)

## Directory Structure
```
jbom-new/
├── src/
│   └── jbom_new/
│       ├── cli/              # CLI entry point
│       ├── core/             # Plugin loader, registries
│       └── plugins/          # Core plugins (empty for now)
├── features/                 # BDD tests
└── tests/                    # Unit tests
```
