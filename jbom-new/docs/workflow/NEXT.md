# What to Do Next

## Current Status (2026-02-27)

jbom-new has reached feature parity with legacy jBOM for core BOM generation:
- **Phases 1–5** complete and merged to main (PRs #57, #61, #63, #64, #66, #67)
- All CLI commands working: `bom`, `pos`, `parts`, `inventory`
- Fabricator profiles (JLC, PCBWay, generic) with field synonyms and tier rules
- Sophisticated inventory matching with priority ordering
- Field system with presets, custom field selection, and consistent CSV/console output
- Validated against 11 real KiCad production projects (see `docs/architecture/workflow-architecture.md`)
- 243 pytest tests + 192 BDD scenarios passing

**Remaining for feature parity**: Harvest `search` and `inventory-search` commands from legacy jBOM.

**Explicitly out of scope**: The `annotate` command (back-annotation to schematics) is deferred to a future phase.

---

## Phase 6: Search Command Harvest

**Goal**: Port the Mouser API search and inventory-search capabilities from legacy jBOM into jbom-new's architecture, integrated with the supplier profile system.

### Legacy Code to Harvest

All source paths are relative to `~/Dropbox/KiCad/jBOM/src/jbom/`:

- **`search/__init__.py`** — `SearchProvider` ABC and `SearchResult` dataclass (~50 lines, clean abstractions)
- **`search/mouser.py`** — `MouserProvider` with Mouser keyword API integration (~170 lines)
- **`search/filter.py`** — `SearchFilter` (parametric filtering) and `SearchSorter` (stock/price ranking) (~100 lines)
- **`cli/commands/builtin/search.py`** — `search` CLI command (~150 lines)
- **`cli/commands/builtin/inventory_search.py`** — `inventory-search` CLI command (~590 lines, includes scoring, reporting, CSV export)
- **`processors/search_result_scorer.py`** — Priority scoring for search results against inventory items


### non-functional constraints

- Web APIs like Mouser's have restrictive rate and bandwidth limits that are easy to trigger, especially during development.  For that reason, agressive caching, local query pre-optimization and strategic query engineering are high priorities.

### jbom-new Target Architecture

Active development directory: `~/Dropbox/KiCad/jBOM/jbom-new`
PYTHONPATH: `~/Dropbox/KiCad/jBOM/jbom-new/src`

**Where new code should go:**
- `src/jbom/services/search/` — Search provider abstraction, Mouser provider, filtering/scoring
- `src/jbom/cli/search.py` — `jbom search` CLI command
- `src/jbom/cli/inventory_search.py` — `jbom inventory-search` CLI command
- `tests/services/search/` — Unit tests for search services
- `features/search/` — BDD scenarios for search commands

**Integration points:**
- `src/jbom/cli/main.py` — Register new subcommands
- `src/jbom/config/fabricators.py` — Supplier profiles may inform search context (e.g., which distributor to search)
- `src/jbom/common/types.py` — May need `SearchResult` type or similar

### Deliverables

#### 6.1: Search Provider Infrastructure
- Port `SearchProvider` ABC and `SearchResult` dataclass to `src/jbom/services/search/`
- Port `MouserProvider` (Mouser API integration)
- Port `SearchFilter` and `SearchSorter`
- Requires `MOUSER_API_KEY` environment variable
- Unit tests that work WITHOUT an API key (mock the API)

#### 6.2: `jbom search` Command
- Simple keyword search: `jbom search "10k resistor 0603"`
- Options: `--provider`, `--limit`, `--api-key`, `--all` (disable filters), `--no-parametric`
- Console table output with manufacturer, MPN, price, availability
- BDD scenarios for CLI integration

#### 6.3: `jbom inventory-search` Command
- Bulk search: `jbom inventory-search SPCoast-INVENTORY.csv`
- Options: `--output`, `--report`, `--provider`, `--limit`, `--api-key`, `--dry-run`, `--categories`
- Dry-run mode (validates input, shows what would be searched, no API calls)
- Scoring/ranking of search results against inventory items
- Analysis report generation (category breakdown, success rates, failure analysis)
- Enhanced inventory CSV export with search candidates
- BDD scenarios including dry-run validation

### Testing Constraints

- **Unit tests**: Must work without API key (use mocks/fixtures for Mouser responses)
- **Dry-run mode**: Enables integration testing without API calls
- **API tests**: Gate behind `MOUSER_API_KEY` environment variable (skip if not set)
- **BDD**: Gherkin scenarios for CLI behavior, not API integration
- Run `python -m behave --format progress` from `jbom-new/` — all scenarios must pass
- Run `python -m pytest tests/` — all tests must pass

### Architecture Conventions (follow existing patterns)

- **Type hints required** on all functions
- **Docstrings required** for public methods
- **Dataclasses** for structured data
- **Services** contain business logic; CLI provides thin wrappers
- **Single responsibility** per service
- See `src/jbom/cli/bom.py` and `src/jbom/services/bom_generator.py` for the pattern

### Workflow

Follow the A-B-C pattern from `WARP.md`:
- **A**: Create feature branch from main (e.g., `feature/phase-6-search-harvest`)
- **B**: Frequent commits with semantic messages, co-author attribution
- **C**: Create PR with comprehensive description, link deliverables

---

## Future Phases (not in scope for Phase 6)

- **Phase 7**: `annotate` command — back-annotate inventory data to KiCad schematics (round-trip workflow)
- **Phase 8**: Advanced property matching — IPN conflict detection, tolerance/voltage-aware scoring
- **Match diagnostics** — `--debug` flag showing why components matched (or didn't) specific inventory items

## SEE ALSO
- `docs/architecture/workflow-architecture.md` — Pipeline architecture, service mapping, real-project validation results
- `docs/architecture/adr/0001-fabricator-inventory-selection-vs-matcher.md` — ADR on fabricator selection design
- `docs/architecture/anti-patterns.md` — Patterns to avoid
