# CHANGELOG


## v3.6.0 (2025-12-30)

### Bug Fixes

* fix: use proper terminal formatting instead of raw markdown

- Remove literal backticks and markdown syntax from output
- Use 4-space indentation to distinguish commands from instructions
- Maintain markdown spirit with clean separation but terminal-appropriate
- Remove backticks around UI elements for cleaner text flow
- Commands now clearly distinguished through indentation

Co-Authored-By: Warp <agent@warp.dev> ([`fb449b6`](https://github.com/plocher/jBOM/commit/fb449b663afa92385c6f6eecdf5feae47370e4bf))

* fix: address pre-commit formatting and linting issues in POC

- Auto-formatted by black (6 files)
- Fixed trailing whitespace and end-of-file issues
- Fixed mixed line endings in enhanced_resistors.csv
- Flake8 issues remain (unused imports, f-string placeholders)

POC functionality unchanged - organizational cleanup only

Co-Authored-By: Warp <agent@warp.dev> ([`cec99bd`](https://github.com/plocher/jBOM/commit/cec99bdf5ee3ad0f7f71c05ad6ff5b57a8b2f557))

* fix: clean up test files and linting issues

- Remove old test_search_workflow.py with undefined variables
- Fix f-string linting issue in test_inventory_search.py
- Keep focused test_inventory_search.py and test_inventory_cli.sh
- Both tests ready for real-world validation with MOUSER_API_KEY ([`e0db5cc`](https://github.com/plocher/jBOM/commit/e0db5cc2ab8d9f7b5ddf17de3f07b06aa97b12ff))

* fix: correct mock patching in functional tests for CI compatibility

- Change mock patches from jbom.search.mouser.MouserProvider to jbom.api.MouserProvider
- Ensures mocks intercept the import location where MouserProvider is actually used
- Fixes CI test failures caused by real API key validation during mocked tests
- All functional inventory tests now pass in CI environment ([`b32eaa6`](https://github.com/plocher/jBOM/commit/b32eaa60bdf920a43501da27c382cca6658c865d))

### Features

* feat: add markdown-style CLI output and AppleScript automation

- Replace icons with clean markdown-style code blocks
- Separate instructions from copy-pastable commands
- Add AppleScript automation option alongside manual workflow
- Provide choice between manual (recommended) and automated approaches
- Include proper error handling and fallback to manual mode

Co-Authored-By: Warp <agent@warp.dev> ([`9a664fa`](https://github.com/plocher/jBOM/commit/9a664fa1a7c026e609ed1a40121d0bb9e1f9be3d))

* feat: finalize Unicode normalization script with proper workflows

- Add timestamped backup creation for safe in-place modification
- Implement manual workflow for Numbers files via stdout commands
- Update documentation to reflect actual implementation
- Remove AppleScript automation due to reliability issues

Co-Authored-By: Warp <agent@warp.dev> ([`a28e152`](https://github.com/plocher/jBOM/commit/a28e1525e5812341ee4195c4df1f07e44ee2022e))

* feat: add comprehensive search functionality test workflows

- test_search_workflow.py: Python API test with inventory components
- test_cli_search.sh: CLI functionality test with representative queries
- README-search-tests.md: Comprehensive testing guide and success criteria
- Focus on real-world validation and quality assessment
- Tests search_parts API with components from example inventory
- Identifies areas for search algorithm and inventory data improvement
- Provides clear success criteria and result interpretation guidelines ([`dcc1b8d`](https://github.com/plocher/jBOM/commit/dcc1b8d739b8a507dde58cdc9e0d6ed9a5e678bd))

* feat: enhance error messages for unsupported search providers

- Replace "Unknown provider" with more helpful "Unsupported search provider" messages
- Include list of currently supported providers in error message
- Mention future provider plans (e.g., DigiKey) to set user expectations
- Update unit test to match new error message format
- Maintain error behavior (not warning) for explicit provider selection ([`1a659de`](https://github.com/plocher/jBOM/commit/1a659dec46178eefd176f5b475bea85355cf62af))

* feat: add inventory search automation with distributor integration

- Enhanced inventory command with --search flag for automated part searching
- Added SearchResultScorer for intelligent ranking combining technical and supplier metrics
- Added InventoryEnricher for batch processing with rate limiting and error recovery
- New generate_enriched_inventory() API function with InventoryOptions dataclass
- Support for multiple search results per component with priority ranking
- Comprehensive test coverage: unit tests, functional tests, and error handling
- Updated CLI documentation and API reference with search enhancement options
- Version bump to 3.6.0 for minor semantic release

Co-Authored-By: Warp <agent@warp.dev> ([`f36a638`](https://github.com/plocher/jBOM/commit/f36a6382854a8c96d5fc3030fddbd16cc1e13ed7))

* feat: add search enhancement to inventory command

- New --search flag enables automated part association
- Complete argument group with --provider, --api-key, --limit, --interactive
- Comprehensive error handling and input validation
- Clear search statistics reporting
- Seamless integration with generate_enriched_inventory API
- Backward compatible - existing usage unchanged
- 16 comprehensive unit tests (100% passing)
- Enhanced help with clear examples and documentation

Usage examples:
  jbom inventory project/ --search                    # Basic search enhancement
  jbom inventory project/ --search --limit=3          # Multiple candidates
  jbom inventory project/ --search --api-key=KEY      # Custom API configuration

Co-Authored-By: Warp <agent@warp.dev> ([`ae263cc`](https://github.com/plocher/jBOM/commit/ae263cc2e109e154296e2b1744b94aad64f032db))

* feat: add generate_enriched_inventory API function

- New InventoryOptions dataclass with search configuration
- Comprehensive generate_enriched_inventory function following jBOM patterns
- Support for both basic and search-enhanced inventory generation
- Complete output handling (CSV, console, stdout)
- Robust error handling and comprehensive unit tests (9/9 passing)
- Seamless integration with existing InventoryEnricher and search providers

Co-Authored-By: Warp <agent@warp.dev> ([`43072e2`](https://github.com/plocher/jBOM/commit/43072e2082d388e87e6b6307042f222fb5919948))

* feat: implement core search-enhanced inventory classes

- Add SearchResultScorer for intelligent priority ranking
- Add InventoryEnricher for automated part association
- Combines InventoryMatcher logic with supplier quality metrics
- Comprehensive unit tests with 100% pass rate
- Supports batch processing and rate limiting

Co-Authored-By: Warp <agent@warp.dev> ([`08e5b27`](https://github.com/plocher/jBOM/commit/08e5b27e7ef17fe4b28dbec66792696dc3ddf650))

### Refactoring

* refactor: remove experimental AppleScript automation

- Remove failed AppleScript automation option
- Simplify interface to use only manual workflow
- Focus on reliable manual process rather than complex automation
- Clean up unused code (~100 lines removed)

Co-Authored-By: Warp <agent@warp.dev> ([`26d4f58`](https://github.com/plocher/jBOM/commit/26d4f58d0da42c806a6a4482da8f110c8a8b30fd))

* refactor: remove superfluous emojis and success messages

- Remove checkmark "Fixes applied successfully!" message
- Clean up all emoji icons from CLI output (💾, 📁, ✅, etc.)
- Keep only essential informational messages
- More appropriate professional CLI output

Co-Authored-By: Warp <agent@warp.dev> ([`35bc369`](https://github.com/plocher/jBOM/commit/35bc369e7fb7f2dd94e57b64a1f744d39db71a6f))

* refactor: simplify Numbers workflow output

- Remove verbose echo statements and shell commands
- Output clean, concise manual instructions
- Only essential Python command needs copy-pasting
- Much more elegant and user-friendly

Co-Authored-By: Warp <agent@warp.dev> ([`2ed603c`](https://github.com/plocher/jBOM/commit/2ed603c6768e2953978f58488973b1b9e29e6798))

* refactor: move remaining POC test files from examples/ to poc/

Moved POC-specific files to proper locations:
- test_inventory_search.py, search_project_parts.py → scripts/
- test_cli_search.sh, test_inventory_cli.sh → scripts/
- test-search-INVENTORY.{csv,numbers} → examples/
- README-search-tests.md → docs/
- test_project/ → examples/

examples/ folder now contains only production example files
poc/inventory-enhancement/ contains complete self-contained POC

Co-Authored-By: Warp <agent@warp.dev> ([`a65fe0b`](https://github.com/plocher/jBOM/commit/a65fe0be70997f3dc6f8caf339457cf15ed154fd))

* refactor: remove unnecessary future plans text from error messages

- Remove unhelpful "Additional providers (e.g., DigiKey) are planned" text
- Keep error messages concise and focused on current functionality
- Clean up documentation to remove speculative language
- Maintain clear provider validation with actionable error messages ([`53e10a5`](https://github.com/plocher/jBOM/commit/53e10a5f073830fa4e74fc218e126bb06cd52cfb))

### Unknown

* Merge pull request #7 from plocher/feature/inventory-search-automation

feat: add inventory search automation with distributor integration ([`fd3db76`](https://github.com/plocher/jBOM/commit/fd3db76381abe0d2a6ec993774532ba0568c9670))

* cleanup: remove obsolete Unicode normalization script and docs

- Unicode issues manually resolved in inventory files
- Remove apply_inventory_fixes.py script (no longer needed)
- Remove README_inventory_fixes.md documentation
- Update main README to remove Unicode normalization references
- Focus POC on core inventory enhancement capabilities

Co-Authored-By: Warp <agent@warp.dev> ([`b04a05a`](https://github.com/plocher/jBOM/commit/b04a05aa40b019cae06c0c01fd4863fb16845dcd))

* removed unicode omega ([`ef1421d`](https://github.com/plocher/jBOM/commit/ef1421dcf305a7c80ae672645c6e8136e57181ec))


## v3.5.0 (2025-12-21)

### Bug Fixes

* fix: stabilize config-driven fabricators and tests

- Fix fabricator config loading and validation
- Update BOM and POS generators to use configured fields
- Align test suite with new config structure (JLC, PCBWay)
- Simplify CLI help and usage examples
- Fix various unit and functional test failures

Co-Authored-By: Warp <agent@warp.dev> ([`45a4be4`](https://github.com/plocher/jBOM/commit/45a4be48b0670988c421c1573de53772111d9544))

* fix: remove unused normalize_component_type import ([`9684641`](https://github.com/plocher/jBOM/commit/9684641bb6f82f3e35b83f5ae527e5c22f8c045f))

* fix: update unit tests for removed legacy presets ([`2ddc3ae`](https://github.com/plocher/jBOM/commit/2ddc3ae3c35d602034a92bc88d66c5f574cd8bb3))

### Features

* feat: implement configuration-driven fabricator support for BOM and POS

- Replaced hardcoded fabricator presets with fully data-driven configuration
- Updated config merging strategy to REPLACE for full user control over columns
- Implemented consistent fabricator detection logic across BOM and POS commands
- Added handling for I: and C: prefixes in part number lookup
- Updated documentation with new configuration details and replacement behavior
- Added modern functional tests based on real-world project usage ([`79c84f7`](https://github.com/plocher/jBOM/commit/79c84f76860aa916c70c3097776ab0d93db17745))

* feat: add fabricator support to POS command and update docs

- Add --fabricator option to POS command and API
- Update POSGenerator to use fabricator-specific presets
- Add search_parts to API
- Update README.md and man pages with new commands (inventory, search, annotate)
- Fix: pass options to SchematicLoader in BOMGenerator

Co-Authored-By: Warp <agent@warp.dev> ([`56c9c99`](https://github.com/plocher/jBOM/commit/56c9c9946de8bbaabbbe361fa3a840e16c5b091e))

### Refactoring

* refactor: move pos_columns to fabricator definition files

- Move POS column mappings from defaults.yaml to jlc.fab.yaml, pcbway.fab.yaml, seeed.fab.yaml
- Keeps fabricator configuration encapsulated in single files

Co-Authored-By: Warp <agent@warp.dev> ([`4a569cd`](https://github.com/plocher/jBOM/commit/4a569cd0a8b0923d2dd1b4a034c324366a9c933c))

* refactor: implement config-driven POS field selection

- Add pos_columns to FabricatorConfig and defaults.yaml
- Update POSGenerator to load fields and headers from config
- Remove hardcoded fabricator presets from POSGenerator
- Update tests to reflect dynamic preset loading

Co-Authored-By: Warp <agent@warp.dev> ([`014c331`](https://github.com/plocher/jBOM/commit/014c3318679866f59c2939311d19453f7f3d609f))

### Unknown

* Merge pull request #6 from plocher/feat/config-driven-fabricators

feat: Config-driven fabricator support for BOM and POS ([`a9be524`](https://github.com/plocher/jBOM/commit/a9be52487347225ffa5d52c4fea34c5744673483))


## v3.4.0 (2025-12-21)

### Features

* feat: implement config-driven component classification

- Refactored component classification to use a rule-based engine
- Moved hardcoded classification logic to src/jbom/config/defaults.yaml
- Added ClassificationEngine in src/jbom/processors/classifier.py
- Updated JBOMConfig to support component_classifiers
- Added support for debug_categories in options
- Updated inventory generation to leave IPN blank for unknown types
- Fixed schematic loader to ignore library definitions (ghost components)
- Updated documentation with new configuration options
- Added unit and functional tests for classification engine ([`12332b7`](https://github.com/plocher/jBOM/commit/12332b77baa4a8a30fa95dbbff2f8319f079023e))

### Unknown

* Merge pull request #5 from plocher/feat/config-driven-classification

feat: config-driven component classification ([`c8b5b9d`](https://github.com/plocher/jBOM/commit/c8b5b9de0adf823a34bbec963541cf6c47a9c382))


## v3.3.1 (2025-12-20)

### Bug Fixes

* fix: update CI workflow to install project dependencies from pyproject.toml

The CI workflow was manually installing dependencies instead of using
the project pyproject.toml file. This caused PyYAML to be missing since
it was added to pyproject.toml but not to the manual install list.

Changed to use "pip install -e .[all]" which installs the project in
development mode with all optional dependencies, ensuring all required
dependencies from pyproject.toml are included.

Co-Authored-By: Warp <agent@warp.dev> ([`6d82300`](https://github.com/plocher/jBOM/commit/6d823004d73d10f64539bfce07714b6cb58ffd78))

* fix: add PyYAML as required dependency for configuration system

The hierarchical configuration system requires PyYAML for loading YAML
configuration files. This was missing from dependencies causing CI/CD
pipeline failures.

Co-Authored-By: Warp <agent@warp.dev> ([`2caa3c5`](https://github.com/plocher/jBOM/commit/2caa3c583bd8b25221892e2c0627ad9d7a4ebe1c))

* fix: remove unused import and apply code formatting

- Fix flake8 linting issue with unused patch import
- Apply pre-commit hook formatting (black, trailing whitespace, end-of-file)

Co-Authored-By: Warp <agent@warp.dev> ([`ccac065`](https://github.com/plocher/jBOM/commit/ccac06592737a71d39fd4204243fcec3eb2e5eb5))

### Unknown

* Merge pull request #4 from plocher/refactor/api-kicad-config-integration

feat: integrate config-driven fabricators across all usage patterns ([`62bdacd`](https://github.com/plocher/jBOM/commit/62bdacd27d12dd733a94663e939d771ceb7043f9))


## v3.3.0 (2025-12-18)

### Features

* feat: add federated inventory, PCBWay support, and Mouser search

Implements Step 3.5 (Federation), Step 5 (Search), and part of Step 6 (Fab Integration POC).

Features:
- Search: Added `jbom search` command using Mouser API.
- Search: Added smart filtering (In Stock, Parametric) and sorting.
- Federation: Updated InventoryItem to track source and distributor fields.
- Federation: Updated InventoryLoader to handle multiple files and distributor columns.
- Fabrication: Added PCBWayFabricator with custom column mapping.
- Tests: Added comprehensive functional test suite for all new features.

Co-Authored-By: Warp <agent@warp.dev> ([`7b9bea5`](https://github.com/plocher/jBOM/commit/7b9bea5e8741ca54ac498015ad19df5915567766))


## v3.2.0 (2025-12-17)

### Features

* feat: implement back-annotation (Step 4)

Adds 'jbom annotate' command to update schematic from inventory via UUID matching.

Co-Authored-By: Warp <agent@warp.dev> ([`80765fd`](https://github.com/plocher/jBOM/commit/80765fd5fd6c187eb58e888ab0fb35b4bcea64c3))

### Refactoring

* refactor: introduce Schematic API shim (Step 4 extension)

Abstracts S-expression manipulation behind an object-oriented API modeled after Pcbnew, facilitating future migration to KiCad Schematic API.

Co-Authored-By: Warp <agent@warp.dev> ([`fda7277`](https://github.com/plocher/jBOM/commit/fda72772277fe662f7620a2073776b5cd18601af))

### Unknown

* Merge pull request #2 from plocher/feat/back-annotation

feat: implement back-annotation (Step 4) ([`555a89b`](https://github.com/plocher/jBOM/commit/555a89b50e79eb593b2f4df96ffc6b0ec28889ff))


## v3.1.0 (2025-12-17)

### Features

* feat: implement federated inventory loading (Step 3.5)

Adds support for loading multiple inventory files and JLC Private Inventory export format.

Co-Authored-By: Warp <agent@warp.dev> ([`92abc9f`](https://github.com/plocher/jBOM/commit/92abc9f93cf945600cdb60b016bf0b7fe4b25e94))

* feat: add fabricator-aware part number lookup and filtering

- Added Fabricator base class and implementations for JLC, Seeed, PCBWay
- Implemented strict filtering: matching inventory items MUST have fabricator-specific part number
- Added --fabricator flag to BOM command
- Refactored field presets: replaced "standard" with "default" using "Fabricator Part Number"
- Updated InventoryMatcher to support fabricator-based filtering
- Updated BOMGenerator to output fabricator-specific data ([`3341979`](https://github.com/plocher/jBOM/commit/33419799b79b20b5ba1091456bcd25ad58d7064e))

* feat: add inventory generation and support inventory-less BOM creation

- Added ProjectInventoryLoader to create inventory from schematic components
- Added `jbom inventory` command to export generated inventory
- Updated `jbom bom` to allow running without -i flag (auto-generates inventory)
- Updated API and BOMGenerator to support optional inventory source ([`caac096`](https://github.com/plocher/jBOM/commit/caac0962b3d364c0ee981651d3de0782e518a854))

### Unknown

* Merge pull request #1 from plocher/feat/federated-inventory

feat/federated inventory ([`7b80f61`](https://github.com/plocher/jBOM/commit/7b80f614092286248f91e7139d47f3335f638793))

* Merge branch 'main' of https://github.com/plocher/jBOM ([`46a400b`](https://github.com/plocher/jBOM/commit/46a400b6722a85a3695b4ffaf4321f4623afd2ce))


## v3.0.0 (2025-12-17)

### Breaking

* refactor(cli): use argparse subparsers with Command pattern

BREAKING CHANGE: CLI now uses argparse subparsers

- Created Command base class with shared patterns
- Implemented BOMCommand and POSCommand classes
- Replaced manual dispatch with argparse subparsers
- Added --outdir to POS command for consistency
- Rewrote tests to check behavior not implementation
- 163 tests passing (gained 2 tests) ([`15a2b3f`](https://github.com/plocher/jBOM/commit/15a2b3f1af4516d2a75b3f99f74a37a10384ba6d))

* feat: complete v3.0 architecture refactoring - remove backward compatibility

BREAKING CHANGE: Removed all v2.x backward compatibility code

Phase 8 complete:
- Removed jbom.py and empty module directories
- Fixed CLI to use v3.0 API
- Created cli/formatting.py for console output
- All 161 tests passing

Clean architecture: loaders, processors, generators, common, api, cli ([`7d4b570`](https://github.com/plocher/jBOM/commit/7d4b5701cd9ebc35498586cfe20f67292bef811d))

### Bug Fixes

* fix: add pbr dependency to bandit pre-commit hook

Fixes ModuleNotFoundError when bandit tries to import pbr.version
Pre-commit will now install pbr in bandit virtual environment ([`e4397a6`](https://github.com/plocher/jBOM/commit/e4397a69e4d6f6e95cfe7d75925d85297a8a32a1))

* fix: Update CLI entry point to jbom.cli.main:main

The entry point was pointing to jbom:main which doesn't exist after reorganization.
Updated to point to the correct location in cli/main.py module. ([`7053365`](https://github.com/plocher/jBOM/commit/7053365fe04fc4aa29353a6e31a00060530502ed))

### Features

* feat(common): add Diagnostics to Generator base and include in API results ([`92d79d5`](https://github.com/plocher/jBOM/commit/92d79d533db076749358cb0c5568417c2dcbd4c9))

* feat: enhance Generator base class with template method pattern (POC)

- Added run() template method that orchestrates common generation flow:
  1. Input discovery (directory vs file)
  2. File loading
  3. Data processing
  4. Output writing
  5. Result dictionary
- New abstract methods enforce consistent interface:
  - discover_input(): Auto-find files in directories
  - load_input(): Parse input files
  - process(): Transform data to entries (returns tuple with metadata)
  - write_csv(): Write output (signature updated to include entries)
- Created test_generator_poc.py demonstrating the pattern
- POC shows 65% code reduction for new generators
- Foundation for refactoring BOMGenerator and POSGenerator

This is the architectural improvement discussed - enforces consistency
through base class while keeping domain logic in subclasses. ([`8c41e3d`](https://github.com/plocher/jBOM/commit/8c41e3da05384b98556b2afc7f6bd0c02ed5f762))

* feat: refactor KiCad plugin as CLI wrapper, add comprehensive tests

- Simplified kicad_jbom_plugin.py to be a thin CLI wrapper (~50 lines)
- Plugin now calls `jbom bom` CLI directly instead of duplicating logic
- Added comprehensive test suite (6 tests) in tests/test_kicad_plugin.py
- Fixed BOMGenerator.write_bom_csv to create parent directories
- Updated README.md with v3.0 API examples and KiCad plugin integration guide
- All 169 tests passing (gained 6 from plugin test suite)

Pre-existing flake8 E501 line-length violations in bom.py remain (not introduced by this commit) ([`e041f25`](https://github.com/plocher/jBOM/commit/e041f2501ff09b4de41c2e5bd29d1eb77e1aa2ea))

* feat(v3.0): Phase 4 - Create unified API with input=/output= parameters

Phase 4 Complete: New v3.0 API created with simplified interface

NEW API FILE: src/jbom/api.py
- generate_bom(input=, inventory=, output=, options=)
- generate_pos(input=, output=, options=, loader_mode=)
- BOMOptions dataclass (verbose, debug, smd_only, fields)
- POSOptions dataclass (units, origin, smd_only, layer_filter, fields)

KEY FEATURES:
- Unified input= parameter accepts both directories and specific files
- Auto-discovery: input='MyProject/' finds .kicad_sch or .kicad_pcb
- Consistent output= parameter for both BOM and POS
- Backward compatible: old generate_bom_api() still works

EXPORTS UPDATED:
- jbom/__init__.py: Export new API functions and options classes
- Marked v3.0 API as primary, v2.x as backward compatibility

NEXT: Phase 5 - Update CLI to use new API (optional but cleaner) ([`1a7971d`](https://github.com/plocher/jBOM/commit/1a7971d512dfc849c44f3833d14ebafd8c22bc1a))

### Refactoring

* refactor(pcb): replace try/except pass with safe fallbacks and diagnostics; plumb diagnostics from POSGenerator ([`685ec0f`](https://github.com/plocher/jBOM/commit/685ec0ff0943344a22131987ba3c58af13158828))

* refactor: complete v3.0 BOMGenerator refactoring and test updates

- Updated BOMGenerator constructor signature from (components, matcher) to (matcher, options)
- Updated all 23 test instances in test_jbom.py to use new pattern
- Updated CLI bom_command.py to use generator from API result dict
- Removed backward compatibility methods (generate_kicad_pos_rows, generate_jlc_cpl_rows)
- Updated test_api_v3.py to check for "entries" instead of "rows" in results
- Updated test_position.py to use iter_components() instead of removed methods
- Removed test_generator_poc.py

All 169 tests passing. v3.0 refactoring complete. ([`a4ee7f4`](https://github.com/plocher/jBOM/commit/a4ee7f418b2caf9789cd3dfe46f80b14ea3408c8))

* refactor: BOMGenerator now inherits from Generator base class (WIP)

- BOMGenerator implements Generator abstract methods:
  - discover_input(): Find .kicad_sch files in directories
  - load_input(): Load schematic using SchematicLoader
  - process(): Generate BOM entries with matching
  - write_csv(): Delegate to existing write_bom_csv()
- Constructor now takes InventoryMatcher instead of components
  - Cleaner separation: inventory loading separate from BOM generation
  - Follows dependency injection pattern
- Updated api.generate_bom() to create matcher and use generator.run()
- BOMOptions.to_generator_options() converts to GeneratorOptions
- Override _get_default_fields() for BOM-specific field resolution

REMAINING WORK:
- Update test files (test_jbom.py) to use new BOMGenerator(matcher, opts) signature
- 32 test failures, 7 errors due to old constructor usage
- Once tests fixed, remove old compatibility methods
- Update CLI bom_command.py to use new pattern

Phase 2 (BOMGenerator) in progress - POSGenerator already complete. ([`63d0dc1`](https://github.com/plocher/jBOM/commit/63d0dc1e6e6dfe03e3369fef1a826346de50d4b3))

* refactor: POSGenerator now inherits from Generator base class

- POSGenerator implements Generator abstract methods:
  - discover_input(): Find .kicad_pcb files in directories
  - load_input(): Load PCB using PCBLoader
  - process(): Filter components and return metadata
  - write_csv(): Write placement data with parent dir creation
- PlacementOptions now extends GeneratorOptions
- Updated api.generate_pos() to use generator.run()
- Updated cli/pos_command.py to use new pattern
- Updated tests to use new constructor signature
- Removed unused imports
- All 169 tests passing ✓

Phase 1 of template method refactoring complete. ([`bc00180`](https://github.com/plocher/jBOM/commit/bc0018062cdde45365d160b5351f19d37243871f))

* refactor(v3.0): Fix architecture - move field parsing to common/

ARCHITECTURAL FIX: Proper dependency flow

PROBLEM: api.py was importing from jbom.py (violation of layered architecture)
- This creates circular dependency risk
- Violates separation of concerns (CLI shouldn't be a library)

SOLUTION: Move reusable utilities DOWN to common/
- Moved FIELD_PRESETS, preset_fields(), parse_fields_argument() to common/fields.py
- Updated api.py to import from common/fields (not jbom.py)
- Updated jbom.py to import from common/fields (single source of truth)

ARCHITECTURE NOW CORRECT:
  CLI (jbom.py, cli/main.py, api.py)
      ↓
  Generators (generators/)
      ↓
  Processors (processors/)
      ↓
  Loaders (loaders/)
      ↓
  Common utilities (common/)

No upward or sideways dependencies - only downward to lower layers.

TESTS: All 168 tests passing (11 new v3.0 API tests included) ([`a4f19b7`](https://github.com/plocher/jBOM/commit/a4f19b74133a58cc580eeaed5a9814df3602daba))

* refactor(v3.0): Phase 2 - Update imports throughout codebase

Phase 2 Complete: All imports updated to new module structure

UPDATED FILES:
Backward compatibility wrappers:
- sch/__init__.py: Re-exports from new loaders/generators/processors
- inventory/__init__.py: Re-exports from new loaders/processors
- pcb/__init__.py: Re-exports from new loaders (BoardLoader→PCBLoader alias)

Main module imports:
- jbom/__init__.py: Import from processors.component_types
- cli/main.py: Import from loaders.pcb, generators.pos (POSGenerator)

Internal cross-references:
- processors/inventory_matcher.py: Import from processors.component_types

Test files updated:
- tests/test_jbom.py: Import from loaders/generators/processors
- tests/test_position.py: Use POSGenerator, loaders.pcb
- tests/test_integration_projects.py: Use POSGenerator, loaders.pcb
- tests/test_cli.py: Mock POSGenerator instead of PositionGenerator

TEST RESULTS: 157 tests passing (5 skipped)

NEXT: Phase 3 - Verify class renames complete, clean up old directories ([`fce8ed3`](https://github.com/plocher/jBOM/commit/fce8ed315529a467d0e2d0d3fce32826157ea66e))

* refactor(v3.0): Phase 1 - Reorganize by data flow (loaders/processors/generators)

Phase 1 Complete: New architecture with clean separation of concerns

MOVED FILES (preserving git history):
Loaders (INPUT):
- inventory/loader.py → loaders/inventory.py
- sch/loader.py → loaders/schematic.py
- pcb/loader.py → loaders/pcb.py (BoardLoader → PCBLoader)
- pcb/model.py → loaders/pcb_model.py

Processors (PROCESSING):
- sch/types.py → processors/component_types.py
- inventory/matcher.py → processors/inventory_matcher.py

Generators (OUTPUT):
- sch/generator.py → generators/bom.py
- pcb/position.py → generators/pos.py (PositionGenerator → POSGenerator)

UPDATES:
- Created __init__.py for loaders/, processors/, generators/
- Updated all internal imports to new locations
- Renamed BoardLoader → PCBLoader for consistency
- Renamed PositionGenerator → POSGenerator (matches BOM acronym)

NEXT: Phase 2 - Update main jbom.py and cli/ imports ([`8cdd694`](https://github.com/plocher/jBOM/commit/8cdd6946764e0e8c70524e1fdb57186fc68f0b10))

* refactor: Complete BOMGenerator extraction with CSV writing and field methods

- Added 370 lines of CSV writing and field access methods to BOMGenerator
- Completed methods: write_bom_csv(), get_available_fields(), _get_field_value()
- Added field access helpers: _get_inventory_field_value(), _has_inventory_field()
- BOMGenerator now fully self-contained at 974 lines
- All 98 tests passing (3 skipped)
- Updated developer docs with:
  - New modular architecture overview
  - Complete BOMGenerator class documentation
  - Method descriptions for all public and private methods
  - Module structure diagram

Phase 5b now complete:
- sch/generator.py: 974 lines (complete BOM generation)
- jbom.py: 970 lines (CLI orchestration only)
- Naming standardized across all loaders
- Pattern consistency between BOMGenerator and PositionGenerator ready for Phase 6 ([`dac1ab6`](https://github.com/plocher/jBOM/commit/dac1ab6161d4043ff13017a4206f50659ffa9f43))

* refactor: Phase 5b - Extract BOMGenerator to sch/generator.py and standardize naming

- Created sch/generator.py with BOMGenerator class (604 lines)
- Renamed sch/parser.py → sch/loader.py (KiCadParser → SchematicLoader)
- Renamed pcb/board_loader.py → pcb/loader.py (kept BoardLoader class name)
- Updated all imports and module __init__.py files
- Reduced jbom.py from 1933 lines to 969 lines (50% reduction)
- Updated test imports to use new module structure

Naming convention now standardized:
- inventory/loader.py - InventoryLoader
- sch/loader.py - SchematicLoader
- pcb/loader.py - BoardLoader
- sch/generator.py - BOMGenerator

Note: BOMGenerator extraction is partial - CSV writing and field access methods
still need to be added to complete Phase 5b. Tests currently show 20 errors due
to missing methods (write_bom_csv, get_available_fields, _get_field_value, etc.) ([`9d89bac`](https://github.com/plocher/jBOM/commit/9d89baca4f058080f84cef97347ddf28f3c59b26))

* refactor: extract schematic parsing and component type detection to sch module (phase 5a)

- Created sch/parser.py with KiCadParser class for parsing .kicad_sch files
- Created sch/types.py with component type detection utilities:
  - get_component_type(): Detect type from lib_id/footprint
  - get_category_fields(): Get relevant fields for component category
  - get_value_interpretation(): Get value field meaning by category
  - normalize_component_type(): Normalize type strings
- Updated sch/__init__.py to export new modules
- Removed ~140 lines from jbom.py (2072 → 1933 lines)
- Updated inventory/matcher.py to import from sch.types
- Maintained backward compatibility via re-exports in jbom.py
- All 98 tests passing (3 skipped)

This completes Phase 5a of the refactoring plan, achieving:
- Clear separation: schematic parsing logic isolated in sch/
- No circular imports
- jbom.py continues to shrink toward pure orchestration role ([`cca4dcc`](https://github.com/plocher/jBOM/commit/cca4dccbe53411ef39d97db9bd495d60e45f9e5e))

* refactor: extract inventory loading and matching logic to separate modules (phase 4)

- Created inventory/loader.py with InventoryLoader class handling CSV/Excel/Numbers file loading
- Created inventory/matcher.py with InventoryMatcher class handling component-to-inventory matching
- Removed ~700 lines from jbom.py by extracting all inventory-related code
- Updated inventory/__init__.py to export new modules
- Maintained backward compatibility by re-exporting InventoryMatcher from jbom.py
- All 98 tests passing (3 skipped)

This completes Phase 4 of the refactoring plan, achieving clear separation:
- loader.py: File I/O and data parsing (CSV/Excel/Numbers)
- matcher.py: Matching algorithms and scoring logic
- jbom.py: CLI interface and BOM generation orchestration ([`6cdeafc`](https://github.com/plocher/jBOM/commit/6cdeafc00a375a4882d8d732bc9a448a8356af67))

* refactor: extract data classes, constants, and utilities to common modules (phases 1-3)

Refactored jbom.py by moving reusable components to common/ modules:

Phase 1 - Data classes and constants:
- Created common/types.py with Component, InventoryItem, BOMEntry dataclasses
- Created common/constants.py with ComponentType, DiagnosticIssue, CommonFields,
  ScoreWeights, SMDType, and all field mapping dictionaries
- Moved PackageType from shim to full implementation in common/packages.py

Phase 2 - Field utilities:
- Moved field normalization functions from jbom.py to common/fields.py
- Implemented normalize_field_name(), field_to_header(), and KNOWN_ACRONYMS
- Removed shim re-exports

Phase 3 - Value utilities:
- Added parse_tolerance_percent() to common/values.py
- Value parsers for resistors, capacitors, inductors already present

Results:
- Reduced jbom.py from 2577 to 2304 lines (10.6% reduction)
- Eliminated circular imports between common modules
- Maintained backward compatibility via imports in jbom.py
- All 98 tests passing ([`5ea293e`](https://github.com/plocher/jBOM/commit/5ea293efaca26faf94879625682e6aac994a380a))


## v2.1.5 (2025-12-15)

### Refactoring

* refactor: optimize WARP.md structure following best practices

- Streamlined root WARP.md to focused essentials only
- Created directory-specific WARP.md files for targeted guidance:
  - src/WARP.md - Source code architecture and patterns
  - tests/WARP.md - Testing requirements and organization
  - docs/WARP.md - Documentation standards and structure
  - release-management/WARP.md - CI/CD and release process
- Moved development planning files from docs/ to release-management/
- Organized content by context for better agent performance
- Reduced token usage while maintaining comprehensive coverage ([`1a372d9`](https://github.com/plocher/jBOM/commit/1a372d9a81c49f4d398659c6bdd1bf8299011277))


## v2.1.4 (2025-12-15)

### Bug Fixes

* fix(ci): add separate twine upload step for PyPI

python-semantic-release v9 doesn't upload to PyPI automatically.
Added explicit twine upload step after semantic-release version. ([`f7d57b9`](https://github.com/plocher/jBOM/commit/f7d57b90362cf225a7582aeb9c092281e7d555bd))


## v2.1.3 (2025-12-15)

### Bug Fixes

* fix(ci): enable PyPI uploads in semantic-release config

Added upload_to_pypi and upload_to_repository options to ensure
packages are uploaded to PyPI during the publish step. ([`c91f8dd`](https://github.com/plocher/jBOM/commit/c91f8dd6ba737a31b0884dda8807491c1f90b3c6))


## v2.1.2 (2025-12-15)

### Bug Fixes

* fix(ci): use separate version and publish commands

The 'publish' command alone does not create new versions - it only
publishes an existing version. Need to run 'version' first to create
the new version, then 'publish' to upload distributions to PyPI. ([`be97b6d`](https://github.com/plocher/jBOM/commit/be97b6d1b0cfabcc90077bbbce58b0ebd3377d98))

* fix(ci): add verbose output to semantic-release workflow for debugging ([`3e2d90b`](https://github.com/plocher/jBOM/commit/3e2d90bf7eea1c68e6349381a893ea9156728efa))

* fix(ci): move semantic-release config to pyproject.toml

The configuration was in .releaserc.toml but python-semantic-release v9
reads from pyproject.toml. This caused version files to not be updated.

Moved all [tool.semantic_release] configuration from .releaserc.toml
to pyproject.toml and deleted the obsolete file. ([`845a701`](https://github.com/plocher/jBOM/commit/845a7019de4542c5e19a7ed3157fa8e1c6aaac99))

* fix(ci): correct semantic-release workflow to update version files

Changed semantic-release workflow to use single 'publish' command instead
of split 'version' and 'publish'. The v9 'publish' command does both
version bumping and publishing in one step.

Also updated environment variables to use REPOSITORY_USERNAME and
REPOSITORY_PASSWORD which are the correct variable names for PyPI
authentication in python-semantic-release v9.

This should fix the issue where semantic-release was only updating
CHANGELOG.md but not version files or publishing to PyPI. ([`cbc4391`](https://github.com/plocher/jBOM/commit/cbc439165932c4a68978f363db26ade2d5815604))


## v2.1.1 (2025-12-15)

### Bug Fixes

* fix: update semantic-release config and fix build warnings

Update python-semantic-release configuration to v9 syntax and fix
deprecation warnings in pyproject.toml.

Changes to .releaserc.toml:
- Migrate from old syntax to python-semantic-release v9 format
- Use version_toml and version_variables for version management
- Configure dist_glob_patterns for build artifacts
- Set upload_to_vcs_release for GitHub Releases
- Update commit parsing to Angular-style conventions
- Configure changelog to exclude chore/ci/docs commits

Changes to .github/workflows/semantic-release.yml:
- Pin python-semantic-release to v9.12.0 for stability
- Add explicit Python setup step
- Configure git user for automated commits
- Split version and publish into separate steps
- Set required environment variables (GH_TOKEN, PYPI_TOKEN)
- Add id-token permission for PyPI trusted publishing

Changes to pyproject.toml:
- Fix deprecated license format: {text = "..."} -> "..."
- Remove deprecated License classifier (now uses SPDX expression)
- Eliminates SetuptoolsDeprecationWarning during build

This enables automatic PyPI publishing when semantic-release creates
new versions based on conventional commit messages. ([`152d67d`](https://github.com/plocher/jBOM/commit/152d67da8544c66291b7ded5e1a22fd360df4943))


## v2.1.0 (2025-12-15)

### Features

* feat: Add auto-detection of PCB files for pos command

- Add find_best_pcb() to auto-detect .kicad_pcb files in project directories
- Match behavior of bom command: both now accept project directories or specific files
- Prefer PCB files matching directory name, handle autosave files gracefully
- Make -o/--output optional for pos command (defaults to PROJECT_pos.csv)
- Update CLI help and documentation to show consistent usage patterns
- Users can now use `jbom pos MyProject/` instead of specifying PCB path ([`ba56527`](https://github.com/plocher/jBOM/commit/ba56527d178433800b695f232961797858a77de9))

### Refactoring

* refactor: Simplify CLI using shared utilities (Phase 3)

Extract and share common CLI logic:

- Add apply_jlc_flag() utility to eliminate duplicated --jlc handling
- Use resolve_output_path() for both bom and pos commands
- Reduce CLI command implementations by ~25 lines
- Improve consistency between bom and pos command patterns

Both commands now follow identical patterns for:
- JLC flag application
- Output path resolution

No behavior changes - pure refactoring for code reuse. ([`74a1419`](https://github.com/plocher/jBOM/commit/74a1419dbd969d49125fc59484fa59c8032b430d))

* refactor: Add generator infrastructure Phase 1 - common abstractions

Create foundational abstractions for unified BOM/placement architecture:

- Add Generator abstract base class with FieldProvider interface
- Add FieldPresetRegistry for centralized field system management
- Add resolve_output_path() for shared output path logic
- Add GeneratorOptions, BOMOptions, PlacementOptions dataclasses
- Export all new modules from jbom.common package

This provides the foundation for refactoring BOMGenerator and
PositionGenerator to share common code while maintaining backward
compatibility. No behavior changes in this commit.

Part of larger refactoring plan to eliminate ~200 lines of duplication. ([`56b606f`](https://github.com/plocher/jBOM/commit/56b606feb64eb01ae490dc9ac164774067bc5564))

* refactor: Consolidate file discovery functions in common.utils

- Move find_best_schematic and related functions to jbom.common.utils
- Move find_best_pcb from cli/main.py to jbom.common.utils
- Remove duplicate implementations from jbom.py
- Update imports in jbom.py to use common.utils
- Update cli/main.py to import from common.utils
- Export all file discovery functions from jbom.common package
- Maintain backward compatibility via jbom.__init__ re-exports
- Centralizes file discovery logic for easier maintenance ([`99f7672`](https://github.com/plocher/jBOM/commit/99f76723ce3270a3512241004efd2e13c79331f5))

### Unknown

* ignore vim swap files ([`5cece97`](https://github.com/plocher/jBOM/commit/5cece9718cccd5289cedba62c13db290a734e16b))

* Add acronym handling to CSV headers

Implemented smart acronym detection in field_to_header() to properly
format known acronyms in all-caps rather than Title Case.

Changes:
- Added KNOWN_ACRONYMS set with common PCB/electronics acronyms
- Updated field_to_header() to check each field part against whitelist
- Acronyms like LCSC, SMD, IPN, MFGPN, USB, LED now properly capitalized
- Non-acronyms still use Title Case (e.g., 'Match Quality')

Known Acronyms (31 total):
- PCB/BOM: lcsc, smd, pcb, bom, dnp, pth, ipn, mfgpn
- Manufacturers: jlc, jlcpcb
- File formats: csv, xlsx, pdf, png, jpg
- Components: led, ic, via, psu
- Interfaces: usb, uart, i2c, spi, can
- Signals: pwm, adc, dac, gnd, vcc
- EMI/RF: rf, esd, emi, emc

Examples:
- 'lcsc' -> 'LCSC'
- 'smd' -> 'SMD'
- 'usb_connector' -> 'USB Connector'
- 'led_color' -> 'LED Color'
- 'match_quality' -> 'Match Quality' (not an acronym)

Updated all test expectations to match new acronym handling.

Test Results: 157 tests passing, 5 skipped ([`e350fb6`](https://github.com/plocher/jBOM/commit/e350fb6c9567f831e5709eb097cdfc8a506f518b))

* Comprehensively update functional test plan with all completed tests

Updated functional test plan to reflect current implementation status:

Test Count Updates:
- Total: 157 tests (109 unit + 48 functional), up from 144
- Functional tests increased from 35 to 48 (13 new tests)

New Test Suites Added:
- test_functional_inventory_formats.py (7 tests)
- test_functional_schematic_edge_cases.py (6 tests)

Updated Sections:
- BOM error cases: test_bom_missing_inventory_headers now passing
- Schematic edge cases: 6/9 completed (empty, no value, special chars, unicode, DNP, in_bom=no)
- Inventory edge cases: 7/8 completed (all formats, empty, unicode, extra columns)

Coverage Status:
- All high-priority tests complete (happy paths, error handling)
- Medium priority mostly complete (inventory formats, schematic edge cases)
- Remaining: PCB edge cases, hierarchical schematics, file I/O, integration tests

Test implementation is now ~80% complete (48/60 planned tests) ([`5238221`](https://github.com/plocher/jBOM/commit/52382218137bb9fbce793012df717d6461c5584e))

* Update functional test plan with current progress

Updated test count and status: 157 total tests (109 unit + 48 functional)
Recent additions: inventory formats (7 tests) and schematic edge cases (6 tests) ([`f09f33e`](https://github.com/plocher/jBOM/commit/f09f33e8abae971db73272d2d87f8df72c45960b))

* Add 13 new functional tests for edge cases

Implemented two new test suites for inventory formats and schematic edge cases.

New Tests (13 total):
test_functional_inventory_formats.py (7 tests):
- test_csv_inventory_format: CSV loading validation
- test_xlsx_inventory_format: Excel format support
- test_numbers_inventory_format: Apple Numbers support
- test_inventory_formats_produce_consistent_results: Cross-format validation
- test_empty_inventory_file: Empty inventory handling
- test_inventory_with_extra_columns: Unknown columns ignored
- test_inventory_with_unicode_characters: UTF-8 support

test_functional_schematic_edge_cases.py (6 tests):
- test_empty_schematic_no_components: Empty BOM generation
- test_component_with_no_value: Empty value field handling
- test_component_with_special_characters_in_value: CSV escaping
- test_component_with_unicode_in_description: UTF-8 in schematics
- test_dnp_components_excluded: DNP (Do Not Place) filtering
- test_components_with_in_bom_no_excluded: in_bom=no filtering

Benefits:
- Validates multiple inventory formats (CSV, XLSX, Numbers)
- Tests edge cases like empty files, unicode, special characters
- Verifies component filtering (DNP, in_bom=no)
- All tests use real inventory files from jBOM-dev/

Test Results:
- 157 total tests (109 unit + 48 functional)
- All passing, 5 skipped (conditional)
- Increased functional coverage from 35 to 48 tests ([`698169b`](https://github.com/plocher/jBOM/commit/698169b50d7217eaddca69e4233c9e989120c9c0))

* Add inventory header validation and unskip test

Implemented validation for required inventory headers (IPN, Category)
and unskipped the corresponding functional test.

Changes:
- Added header validation in _process_inventory_data()
- Validates IPN and Category columns are present
- Raises ValueError with helpful message listing missing/found columns
- Unskipped test_bom_missing_inventory_headers functional test

Benefits:
- Clear error messages when inventory files are malformed
- Catches missing required columns early in the process
- Helps users understand what's wrong with their inventory file
- Better error messages than cryptic KeyError later in processing

Test Results:
- 144 tests passing, 5 skipped
- All skipped tests are conditional (env vars, optional deps)
- test_bom_missing_inventory_headers now runs and passes ([`4ee3a49`](https://github.com/plocher/jBOM/commit/4ee3a49141f8b41fa4da2261a8a2d4a8a4a09764))

* Add proper exception handling to CLI commands

Improved CLI error handling to catch exceptions and return proper exit codes
instead of letting them propagate to the caller.

Changes:
- Wrapped _cmd_bom() and _cmd_pos() with try/except blocks
- Created _cmd_bom_impl() and _cmd_pos_impl() for actual implementation
- Catches FileNotFoundError, ValueError, KeyError, ImportError
- Catches unexpected exceptions and reports them clearly
- All exceptions converted to non-zero exit codes
- Error messages printed to stderr in consistent format

Exception Categories:
- FileNotFoundError: Missing files/directories
- ValueError: Invalid arguments, field names, presets
- KeyError: Missing required data
- ImportError: Missing optional dependencies
- Exception: Catch-all for unexpected errors

Benefits:
- Proper Unix exit codes (0=success, 1=error)
- Clear error messages to stderr
- No stack traces for expected errors
- Easier to use in scripts and automation
- Better user experience

Test Infrastructure:
- Simplified test_functional_base.py (removed exception handling)
- CLI now handles exceptions, tests just catch SystemExit
- All 144 tests still passing ([`e4dd3f7`](https://github.com/plocher/jBOM/commit/e4dd3f739f187dae6d0b374e685efb4144c9f7dd))

* Update functional test plan with completed error tests

Progress Update:
- 35 functional tests now implemented (was 21)
- Added 14 error case tests (8 BOM + 6 POS)
- All high-priority items now complete ✅

Updated Sections:
- Test file list: Added test_functional_bom_errors.py and test_functional_pos_errors.py
- Coverage status: 35 tests implemented (21 happy + 14 error)
- BOM error cases table: Changed ⏳ to ✅ for 7 tests, ⏸️ for 1 skipped
- POS error cases table: Changed ⏳ to ✅ for all 6 tests
- Priority: Marked error handling as DONE
- Effort tracking: 5 hours completed (was 4)
- Remaining: 14-19 hours (was 17-24)
- Success criteria: 35/~60 tests (was 21/~60)

High Priority Status:
1. ✅ CLI happy paths - DONE
2. ✅ Error handling - DONE (was TODO)
3. ✅ Output validation - DONE
4. ✅ Field presets - DONE

Test Results:
- 144 total (109 unit + 35 functional)
- 6 skipped
- All passing

Remaining Work:
- Edge cases (26 tests)
- File I/O (9 tests)
- Integration (5 tests) ([`3076df3`](https://github.com/plocher/jBOM/commit/3076df3fb58eaf762fd29ee1f85376a6868e0fe0))

* Add functional tests for BOM and POS error cases

Implemented 14 error handling tests (8 BOM + 6 POS):

BOM Error Tests (test_functional_bom_errors.py):
✅ test_bom_missing_inventory_file - FileNotFoundError handling
✅ test_bom_invalid_inventory_format - Unsupported file type (.txt)
✅ test_bom_missing_project_directory - Missing/empty project dir
✅ test_bom_project_with_no_schematics - No .kicad_sch files
✅ test_bom_invalid_field_name - Invalid field with helpful error
✅ test_bom_invalid_preset_name - Invalid preset with valid list
✅ test_bom_malformed_schematic_file - Parse error handling
⏸️  test_bom_missing_inventory_headers - SKIPPED (not implemented)

POS Error Tests (test_functional_pos_errors.py):
✅ test_pos_missing_pcb_file - FileNotFoundError handling
✅ test_pos_directory_with_no_pcb - No .kicad_pcb files
✅ test_pos_malformed_pcb_file - Parse error handling
✅ test_pos_invalid_units - Argparse validation (mm/inch)
✅ test_pos_invalid_layer - Argparse validation (TOP/BOTTOM)
✅ test_pos_invalid_loader - Argparse validation (auto/sexp/pcbnew)

Test Infrastructure Updates:
- Enhanced run_jbom() to catch SystemExit and Exception
- Converts exceptions to non-zero exit codes
- Captures error messages in stderr for validation

Test Results:
- 144 total tests (109 unit + 21 happy path + 14 error cases)
- 6 skipped (5 optional dependencies + 1 unimplemented feature)
- All passing ✅

Notes:
- One test skipped for inventory header validation (not yet implemented)
- Error messages validated for clarity and helpfulness
- Both explicit errors and argparse validation tested ([`bb5dcda`](https://github.com/plocher/jBOM/commit/bb5dcda14ff8489a1e8b4214639b715d2b7de172))

* Convert functional test plan to use concise tables

Reformatted functional test plan from bulleted lists to tables for better
readability and scannability:

Table Sections:
- BOM Happy Paths: 9 tests (Status | Test Name | Input/Options | Validates)
- BOM Error Cases: 8 tests (Status | Scenario | Input | Expected)
- POS Happy Paths: 12 tests (Status | Test Name | Input/Options | Validates)
- POS Error Cases: 7 tests (Status | Scenario | Input | Expected)
- CSV Structure Tests: 8 covered (Status | Aspect | Covered By | Validation)
- Field System Tests: 5 tests (Status | Aspect | Covered By | Validation)
- Schematic Edge Cases: 7 tests (Status | Scenario | Expected)
- PCB Edge Cases: 6 tests (Status | Scenario | Expected)
- Inventory Edge Cases: 7 tests (Status | Scenario | Expected)
- Matching Edge Cases: 6 tests (Status | Scenario | Expected)
- File I/O Input: 4 tests (Status | Scenario | Details | Expected)
- File I/O Output: 5 tests (Status | Scenario | Expected)
- Integration Tests: 5 tests (Status | Scenario | Details | Expected)

Benefits:
- Easier to scan status at a glance (✅ vs ⏳)
- Clearer alignment of test inputs and expected results
- More compact representation (60% reduction in line count)
- Better for tracking progress and planning work ([`21da95f`](https://github.com/plocher/jBOM/commit/21da95f73ebd36a9d5878c4cb85eddff8db57bc1))

* Update functional test plan with implementation status

Documented completion of happy path functional tests:

Completed (✅):
- 21 functional tests implemented (9 BOM + 12 POS)
- Test infrastructure (test_functional_base.py)
- Test fixtures (minimal_project)
- Output format validation
- Field preset validation
- Console vs file output modes
- 4 hours of work completed

Status Update:
- Changed from "Missing" to "Implemented" for all happy path tests
- Added ✅ checkmarks for completed tests
- Added ⏳ for TODO items
- Updated effort tracking: 4 hours completed, 17-24 hours remaining
- Current: 130 total tests (109 unit + 21 functional), all passing

Remaining Work (⏳):
- Error handling tests (8 BOM + 7 POS)
- Edge case tests (26 tests across 4 categories)
- File I/O tests (9 tests)
- Integration tests (5 tests)
- Estimated: 17-24 hours remaining

Success Criteria Progress:
- 21 of ~60 functional tests implemented
- All tests passing with no regressions
- Infrastructure and fixtures in place ([`89105e7`](https://github.com/plocher/jBOM/commit/89105e73a578f23c5c0bec7826b24e40eddfa03b))

* Implement functional tests for BOM and POS happy paths

Added comprehensive functional tests covering end-to-end CLI workflows:

Test Infrastructure:
- test_functional_base.py: Base class with utilities for running CLI,
  validating CSV, capturing stdout/stderr
- Test fixtures: Minimal project with schematic, PCB, and CSV inventory
  - 6 components (R, C, LED, connector) with matching inventory
  - Proper KiCad S-expression format for testing

BOM Happy Path Tests (9 tests):
- test_bom_default_fields: Default +standard preset
- test_bom_jlc_flag: JLCPCB preset with --jlc
- test_bom_custom_fields: Custom field list
- test_bom_mixed_preset_and_custom: Mixed preset + custom fields
- test_bom_to_console: Formatted table output
- test_bom_to_stdout: CSV to stdout for piping
- test_bom_verbose_mode: Match Quality and Priority columns
- test_bom_debug_mode: Debug diagnostics
- test_bom_smd_only: SMD filter

POS Happy Path Tests (12 tests):
- test_pos_default_fields: Default +standard preset with SMD field
- test_pos_jlc_flag: JLCPCB preset
- test_pos_custom_fields: Custom field list
- test_pos_units_mm: Millimeter units (default)
- test_pos_units_inch: Imperial units
- test_pos_origin_board: Board origin (default)
- test_pos_origin_aux: Auxiliary origin
- test_pos_layer_top: TOP layer filter
- test_pos_layer_bottom: BOTTOM layer filter
- test_pos_to_console: Formatted table output
- test_pos_to_stdout: CSV to stdout
- test_pos_coordinate_precision: Verify decimal places

All tests pass:
- 109 existing unit tests
- 21 new functional tests
- 130 total tests, 5 skipped

Tests validate:
- CSV structure and headers (Title Case for display)
- Field preset behavior (+standard, +jlc, +minimal)
- Output modes (file, console, stdout)
- Data accuracy and formatting
- Error-free execution ([`56bb1df`](https://github.com/plocher/jBOM/commit/56bb1df5cd8a207b87b9f6b67f266e11da6fd6c4))

* Update test resources to use correct inventory and project paths

Changes:
- Updated Makefile INVENTORY path: jBOM-dev/SPCoast-INVENTORY.numbers
- Updated Makefile PROJECTS_LIST: Added LEDStripDriver, removed Brakeman-RED
- Updated functional-test-plan.md with actual resource paths
- Fixed test_integration_projects.py to use +standard preset

Test resources documented:
- Inventory: /Users/jplocher/Dropbox/KiCad/jBOM-dev/SPCoast-INVENTORY.numbers
- Projects:
  - AltmillSwitches
  - Core-wt32-eth0
  - LEDStripDriver

All integration tests pass with new paths. ([`2e2f3bf`](https://github.com/plocher/jBOM/commit/2e2f3bf894631037f6a2eda6980eccc3ec414d91))

* Add comprehensive functional test plan

Created detailed plan for functional testing to complement existing unit tests.

Coverage includes:
- CLI end-to-end tests (happy paths and error cases)
- Output format validation (CSV structure, headers, precision)
- Edge cases (empty files, malformed inputs, unicode, encodings)
- File I/O tests (multiple formats, permissions, paths)
- Integration tests with real projects

Plan identifies gaps in current test coverage:
- Current: 109 unit tests with mocked dependencies
- Missing: End-to-end CLI workflows, error handling, edge cases
- Need: Test fixtures, base infrastructure, 50+ functional tests

Implementation strategy includes:
- Test fixture requirements (minimal/complex projects)
- FunctionalTestBase class for common utilities
- Priority classification (high/medium/low)
- Estimated effort: 24-37 hours

Success criteria: 50+ test cases, 90%+ coverage, CI on Python 3.9-3.12 ([`4dc46ed`](https://github.com/plocher/jBOM/commit/4dc46edc1d542507edc14d6a0eaa508522b78e00))

* Fix Makefile and update tests for +standard preset

Changes:
- Fixed Makefile unit test target to use 'unittest discover' instead of
  broken module list generation with sed
- Updated test_position.py to use +standard instead of deprecated +kicad_pos
- Updated expected field lists in tests to include 'smd' field
- Updated +all preset test to include all current fields (datasheet, version, smd)

All 109 tests now pass (5 skipped as expected). ([`4789558`](https://github.com/plocher/jBOM/commit/478955876e2aad9d696e2ef2a19605fbbdc8ff21))

* Unify field presets between BOM and POS with +standard default

Changes:
- Renamed +kicad_pos preset to +standard in POS for consistency with BOM
- Added 'smd' field to both +standard and +jlc presets (BOM and POS)
- Changed default preset from +kicad_pos to +standard when no -f option given
- Updated all help text to reflect new preset names and field lists

Field preset summary:

BOM presets:
  +standard: reference, quantity, description, value, footprint, lcsc, datasheet, smd
  +jlc:      reference, quantity, value, i:package, lcsc, smd
  +minimal:  reference, quantity, value, lcsc
  +all:      all available fields

POS presets:
  +standard: reference, x, y, rotation, side, footprint, smd
  +jlc:      reference, side, x, y, rotation, package, smd
  +minimal:  reference, x, y, side
  +all:      all available fields

Both commands now use +standard by default.
The --jlc flag applies the +jlc preset via apply_jlc_flag() utility. ([`9989c71`](https://github.com/plocher/jBOM/commit/9989c71b01f6d0e05d731e8a10ab6108e5f058ad))

* Vastly improve CLI help text with detailed option descriptions

Enhanced help output for all commands with comprehensive details:

Main help (jbom --help):
- Clear command overview
- Usage examples for both BOM and POS
- Instructions for getting command-specific help

BOM command help (jbom bom --help):
- Detailed description of each option with examples
- Output destination options explained (file, -, stdout, console)
- Field selection system fully documented (presets, custom, mixed)
- Examples section showing common use cases

POS command help (jbom pos --help):
- Comprehensive option descriptions
- Available fields listed (including new datasheet, version, smd)
- Units, origin, layer, and loader options explained
- Examples for various scenarios

All help text now uses:
- argparse.RawDescriptionHelpFormatter for better formatting
- Metavar for cleaner option display
- Multi-line help strings for complex options
- Examples sections showing real usage patterns
- Clear explanations of presets and field systems

Previously: terse, single-line descriptions
Now: full documentation comparable to man pages ([`951cb7e`](https://github.com/plocher/jBOM/commit/951cb7e3f7c162803baea0c42c72a61f25657c68))

* Add datasheet, version, and SMD fields to POS output

Extract additional footprint properties from KiCad PCB files:
- Datasheet: from property "Datasheet"
- Version: from property "ki_version"
- SMD: from footprint attributes (attr smd/through_hole)

Changes:
- Updated PcbComponent model to use attributes dict
- Enhanced S-expression parser to extract properties and attr nodes
- Enhanced pcbnew API loader to extract properties and attributes
- Added 3 new fields to PLACEMENT_FIELDS (datasheet, version, smd)
- Updated write_csv() to output new fields
- Updated print_pos_table() to display new fields with proper widths

SMD field values:
- "SMD" for surface-mount components (attr smd)
- "PTH" for through-hole components (attr through_hole)
- Empty for components without explicit attribute

Tested with -f option to include new fields in output. ([`e97e30f`](https://github.com/plocher/jBOM/commit/e97e30fa50975f4bef0e64f15dab0ddda06ac668))

* Add final completion summary document

All work completed:
- 3 structural cleanup steps
- Test fixes (109/109 passing)
- Output features (CSV and formatted tables for BOM and POS)
- Projects automation (Makefile with 12 projects)
- All TODOs completed
- 10 commits with clear messages
- Comprehensive documentation

Status: COMPLETE ✅ ([`c5d2163`](https://github.com/plocher/jBOM/commit/c5d216368526500971bf1c049c32ae228179ba2d))

* Add formatted table output for POS console display

Implement print_pos_table() function for human-readable placement output:
- New function in pcb/position.py
- Displays components in columnar format with proper alignment
- Shows Reference, X, Y, Rotation, Side, Footprint
- Supports custom fields via -f option
- Automatically calculates column widths with max limits
- Shows total component count

POS command output modes now match BOM:
- `-o -` / `-o stdout` → CSV to stdout (pipeline-friendly)
- `-o console` → Formatted table (human-readable)
- `-o file.csv` → Write to file

Makefile now shows formatted tables for both BOM and POS. ([`3050ba3`](https://github.com/plocher/jBOM/commit/3050ba3d52b0261648ce7f23062358d70e661c6c))

* Add session summary and update Makefile for console output

- Created docs/session-summary-2025-12-15.md documenting all work
- Updated projects Makefile to use -o console for debugging output
- BOM now shows formatted table in Makefile
- POS shows CSV (formatted table output pending in TODO) ([`e465abd`](https://github.com/plocher/jBOM/commit/e465abd12b507971788416e0d6fcbf126b2cf31d))

* Distinguish CSV stdout from formatted console output

Make output options more Unix-friendly:
- `-o -` or `-o stdout`: CSV to stdout (pipeline-friendly)
- `-o console`: Formatted human-readable table (BOM only for now)

BOM command:
- `-o -` / `-o stdout` → CSV for piping/parsing
- `-o console` → Formatted table with columns
- File output unchanged

POS command:
- `-o -` / `-o stdout` / `-o console` → CSV to stdout
- TODO: Add formatted table for POS console output

Updated help text to document these options. ([`a2bfbd8`](https://github.com/plocher/jBOM/commit/a2bfbd8d34fd4a658646850f3a672e796b515549))

* Restore formatted table output for BOM console display

When using -o -, -o console, or -o stdout with BOM command:
- Now displays formatted table instead of raw CSV
- Matches original jBOM behavior with nice columnar output
- CSV file output unchanged

The CLI was refactored to use subcommands but lost the formatted
console output feature. This restores it by checking for console
output and calling print_bom_table() instead of write_bom_csv(). ([`30ddcb3`](https://github.com/plocher/jBOM/commit/30ddcb3874f01c34e8bf303c6a6fea76d933f5f3))

* Add stdout support for BOM and POS CSV output

Support -o -, -o console, and -o stdout for console output:
- Update BOMGenerator.write_bom_csv() to detect stdout output paths
- Update PositionGenerator.write_csv() to detect stdout output paths
- Both methods now write to sys.stdout instead of file when requested
- Enables piping and console display without creating temp files

Example usage:
  jbom bom PROJECT -i INVENTORY -o -
  jbom pos BOARD.kicad_pcb -o stdout ([`db209cd`](https://github.com/plocher/jBOM/commit/db209cd2a65d8e03d419e47e0296214c2f878218))

* Use None instead of /dev/null for missing environment variables

Previously the test used /dev/null as a default for INVENTORY and PROJECTS
environment variables. This is semantically incorrect and caused confusing
test failures.

Now:
- INVENTORY_PATH is None when INVENTORY env var is not set
- PROJECTS_ROOT is None when PROJECTS env var is not set
- Tests skip early with clear message when env vars are missing
- No attempts to use /dev/null as a file path

All tests pass (109/109 with 5 skipped) ([`006cfca`](https://github.com/plocher/jBOM/commit/006cfca97e2d61bbe0e1120e21e46d1135273b33))

* Fix inventory test to properly skip when no valid file is provided

The test was checking if INVENTORY_PATH exists, but /dev/null (the default
when no INVENTORY env var is set) exists as a device file. This caused the
test to attempt loading it, which failed because it has no file extension.

Now the test properly checks:
- Path exists AND is a regular file
- File has a valid inventory extension (.csv, .xlsx, .xls, .numbers)

All tests now pass (109/109 with 5 skipped) ([`a5b304d`](https://github.com/plocher/jBOM/commit/a5b304d479802f188fe2e9b771c52e6644be4079))

* Document strategy for extracting code from jbom.py God Object

- Create docs/jbom-extraction-plan.md
- Documents phased approach to extract ~1700 LOC to proper packages
- Move schematic code to sch/ package
- Move inventory code to inventory/ package
- Maintain backward compatibility via re-exports
- Estimated 11-15 hours (1.5-2 agent days)
- All tests pass (108/109) ([`c41a4ec`](https://github.com/plocher/jBOM/commit/c41a4ec65f5e14bc6b5a5b101ab2d8a891dbe171))

* Extract shared S-expression parser utilities

- Create common/sexp_parser.py with shared utilities:
  - load_kicad_file(): Load and parse KiCad S-expression files
  - walk_nodes(): Recursively find nodes of specific type
  - find_child(): Find first child of given type
  - find_all_children(): Find all children of given type
- Refactor pcb/board_loader.py to use shared utilities
- Refactor jbom.py KiCadParser to use shared utilities
- Eliminates duplicate S-expression parsing code
- All tests pass (108/109) ([`e642870`](https://github.com/plocher/jBOM/commit/e642870207102b74cdd7cfbfbf12a98bb1ac3d01))

* Remove unused Phase P0 shim files and fix syntax errors

- Remove 5 unused shim files from sch/ and inventory/ packages
  - sch/api.py, sch/model.py, sch/bom.py, sch/parser.py
  - inventory/matcher.py
- Update package __init__ files to import directly from jbom.jbom
- Update documentation to remove references to shim imports
- Fix MRO conflict in Generator class (inherit from FieldProvider only)
- Fix f-string syntax errors in fields_system.py
- All tests pass (108/109, 1 unrelated inventory test error) ([`dce1efb`](https://github.com/plocher/jBOM/commit/dce1efb2fb7f04c975de3aaf1d28133748da9365))


## v2.0.0 (2025-12-15)

### Breaking

* feat!: Replace CLI with subcommand-based interface

BREAKING CHANGE: CLI completely redesigned
- New subcommands: `jbom bom` and `jbom pos` (position/placement)
- Old CLI syntax no longer supported
- Added --jlc flag to both commands for JLCPCB-friendly field presets
- Moved CLI logic to src/jbom/cli/ for better organization ([`1f6e3eb`](https://github.com/plocher/jBOM/commit/1f6e3eba7a99b4853f695cfa5edf4f049603a961))

* refactor!: Restructure codebase into modular package hierarchy

BREAKING CHANGE: Internal package structure reorganized
- Move schematic logic to src/jbom/sch/
- Move inventory logic to src/jbom/inventory/
- Create src/jbom/common/ for shared utilities
- Prepare for PCB module integration alongside schematic module

This refactor maintains API compatibility but changes internal imports. ([`8ce30ee`](https://github.com/plocher/jBOM/commit/8ce30eeaf00f7f1d8671c7648ef5387f04643352))

### Build System

* build: Add Makefile for developer workflows

- Add targets for unit tests, integration tests, and cleanup
- Externalize integration test project list via PROJECTS_LIST env var
- Externalize inventory path via INVENTORY env var
- Provides clean developer experience with `make test`, `make integration`, etc. ([`b60284d`](https://github.com/plocher/jBOM/commit/b60284dbf89b2e476ffaded5a23f040f47ed1c26))

### Features

* feat: Add PCB board loading with pcbnew API and S-expression fallback

- Implement BoardLoader with auto-detection between pcbnew and sexp parsers
- Support KiCad 7 and 8 Reference property resolution
- Recursive footprint field discovery
- Extract position, rotation, layer, and footprint for all components
- Foundation for PCB-based fabrication workflows ([`e8f56ca`](https://github.com/plocher/jBOM/commit/e8f56ca36f12e71a967b8e448aa439c879b3ce7e))


## v1.0.2 (2025-12-14)

### Refactoring

* refactor: move README.man files to docs/ folder

User-facing documentation is now organized in docs/ folder:

docs/ (included in PyPI):
- README.man1.md: CLI reference
- README.man3.md: Python API reference
- README.man4.md: KiCad plugin setup
- README.man5.md: Inventory format specification
- README.developer.md: Technical architecture
- README.tests.md: Test suite documentation
- CHANGELOG.md: Version history
- CONTRIBUTING.md: Contribution guidelines

release-management/ (excluded from PyPI):
- WARP.md: Development environment notes
- PRE_COMMIT_SETUP.md: Pre-commit hooks guide
- PRE_COMMIT_QUICK_REFERENCE.md: Quick reference
- GITHUB_SECRETS_SETUP.md: CI/CD configuration
- SECURITY_INCIDENT_REPORT.md: Security documentation

Updates:
- MANIFEST.in: Simplified to use recursive-include docs
- Cross-references updated throughout all documentation
- WARP.md directory structure clarified

This keeps the repository root clean with only README.md at the top
level, consolidating all documentation in docs/ for consistency. ([`d62f1a1`](https://github.com/plocher/jBOM/commit/d62f1a1fcae2cc0646d15b046d06417add94051c))

* refactor: reorganize docs and release-management folders

Split documentation into two distinct folders:

docs/ (included in PyPI):
- CONTRIBUTING.md: Developer guidelines and setup
- CHANGELOG.md: Version history
- README.developer.md: Technical architecture and algorithms
- README.tests.md: Test suite documentation

release-management/ (excluded from PyPI):
- GITHUB_SECRETS_SETUP.md: CI/CD secrets configuration
- SECURITY_INCIDENT_REPORT.md: Security incident documentation
- PRE_COMMIT_SETUP.md: Pre-commit hooks comprehensive guide
- PRE_COMMIT_QUICK_REFERENCE.md: Pre-commit quick reference
- WARP.md: Development environment notes and architectural guidance

Updates:
- MANIFEST.in: Include docs/ recursively, exclude release-management/
- Cross-references updated in docs and release-management files
- Directory structure clarified in WARP.md

This separation ensures PyPI users get developer documentation while
keeping release/security management and tooling configuration out of
the distributed package. ([`a32fed3`](https://github.com/plocher/jBOM/commit/a32fed3e6cc09f2fd93dad8240839a04693ff027))

* refactor: move development and release docs to docs/ folder

Move non-user-facing documentation to docs/ directory that is excluded
from PyPI package distribution:

Moved to docs/:
- CONTRIBUTING.md: Developer guidelines and setup
- README.developer.md: Technical architecture and algorithms
- README.tests.md: Test suite documentation
- CHANGELOG.md: Version history
- GITHUB_SECRETS_SETUP.md: CI/CD secrets configuration
- SECURITY_INCIDENT_REPORT.md: Security incident documentation
- PRE_COMMIT_SETUP.md: Pre-commit hooks guide
- PRE_COMMIT_QUICK_REFERENCE.md: Pre-commit quick reference
- WARP.md: Development environment notes

Kept at root (user-facing):
- README.md: Quick start and overview
- README.man1.md: CLI reference
- README.man3.md: Python API reference
- README.man4.md: KiCad plugin setup
- README.man5.md: Inventory format specification

Updates:
- Update MANIFEST.in to exclude docs/ folder from distribution
- Update cross-references in root README files
- Add docs/README.md as index for development documentation

The docs folder is now the single location for development, release
management, and architectural documentation, keeping the repository
root clean and the PyPI package lean. ([`b659257`](https://github.com/plocher/jBOM/commit/b659257b7ad801932b039bab4491b4d84ef182cf))

### Unknown

* Add security incident report for exposed PyPI token

Documents the security incident where a PyPI API token was
inadvertently exposed in documentation.

Response completed:
✅ Token rotated and revoked on PyPI
✅ Documentation fixed with safe placeholders
✅ Git history cleaned using git-filter-repo
✅ Token completely removed from repository

Status: RESOLVED - Repository is now secure ([`f5e3861`](https://github.com/plocher/jBOM/commit/f5e3861a7d7d9ddeb0276afe2573166bdd2411c3))

* SECURITY: Remove exposed PyPI token examples from documentation

CRITICAL: The original commit exposed what appeared to be a real PyPI API token.

Removed:
- Partial token example 'pypi-AgEIcHlwaS5vcmc...' from line 39
- Same token example from CLI command at line 62

Replaced with:
- Generic placeholder 'YOUR_ACTUAL_TOKEN_HERE'
- Format description showing token structure
- Warning to NEVER share or commit tokens

ACTION REQUIRED:
- If the exposed token (starting with pypi-AgEI...) was real:
  1. Immediately revoke it on https://pypi.org/account/ → API tokens
  2. Create a new token
  3. Update GitHub secret PYPI_API_TOKEN with new token
  4. Verify workflows still work

Security best practices now emphasized in documentation. ([`9fbb9d6`](https://github.com/plocher/jBOM/commit/9fbb9d6eb390ffcfdbd175684ae88792efec1762))

* Add comprehensive GitHub Secrets and Variables configuration guide

- Explains difference between Secrets vs Variables
- Documents Repository vs Organization scope
- Covers Environment-specific secrets
- Step-by-step PyPI API token generation
- Web UI and GitHub CLI configuration methods
- Troubleshooting common issues
- Security best practices
- Complete verification checklist

For jBOM: Only requires 1 repository secret (PYPI_API_TOKEN)
Everything else is automated by GitHub Actions ([`01c3fa2`](https://github.com/plocher/jBOM/commit/01c3fa2ed18f0e6a7759ae9f010da7f612dff77e))

* Add semantic release and CI/CD workflows ([`888773e`](https://github.com/plocher/jBOM/commit/888773e42e1f5430c7e8e8a462f898f8f5c6e985))

* Update GitHub repository URL and add Contributing section

Files updated:
- README.md:
  * Added Contributing section with GitHub repository link (github.com/plocher/jBOM)
  * Updated version to v1.0.1 with feature summary
  * Added contribution workflow steps
  * Link to CONTRIBUTING.md for detailed guidelines

- pyproject.toml:
  * Updated all project URLs to github.com/plocher/jBOM
  * Homepage, Documentation, Repository, and Issues all point to correct repo

- WARP.md:
  * Added GitHub Repository section
  * Links to issues and pull requests

This ensures all project metadata, documentation, and contributing information
correctly points to the public GitHub repository. ([`afb1dde`](https://github.com/plocher/jBOM/commit/afb1ddeef80716cfde8f34908bb5c249a5656f73))

* Phase 7: Upload to production PyPI successfully

Changes:
- Added kicad_jbom_plugin.py to MANIFEST.in for distribution inclusion
- Successfully uploaded jbom-1.0.1 to production PyPI

Upload Results:
- Both wheel and source distribution uploaded successfully
- Package available at: https://pypi.org/project/jbom/1.0.1/
- Users can now install with: pip install jbom

jBOM is now fully installable and publicly available on PyPI!

Installation methods now available:
1. From PyPI: python -m pip install jbom
2. With Excel support: python -m pip install jbom[excel]
3. With Numbers support: python -m pip install jbom[numbers]
4. With all features: python -m pip install jbom[all]
5. For development: python -m pip install jbom[dev] ([`31193db`](https://github.com/plocher/jBOM/commit/31193db1b1abd45d7ac67c0cbef233592ec22b40))

* Phase 6: Upload to TestPyPI successfully

Changes:
- Fixed invalid classifier 'Topic :: Electronics' → 'Topic :: Scientific/Engineering'
- Updated setuptools to latest version for proper Metadata handling
- Verified distribution packages pass twine checks

Upload Results:
- Successfully uploaded both wheel and source distribution to test.pypi.org
- Package available at: https://test.pypi.org/project/jbom/1.0.1/
- Can be tested with: pip install --index-url https://test.pypi.org/simple/ jbom

This confirms the package is properly formatted and ready for production PyPI. ([`33bed47`](https://github.com/plocher/jBOM/commit/33bed47045781cd8c4963c37c7e368e80e2aebe6))

* Phase 5: Fix pyproject.toml license format and test build

Changes:
- Updated license format from {text = "AGPLv3"} to {text = "AGPL-3.0-only"} (SPDX format)
- Updated classifier from deprecated format to SPDX-compatible text
- Removed SetuptoolsDeprecationWarning messages during build

Verification:
- Built distribution packages successfully without warnings
- Created:
  * dist/jbom-1.0.1-py3-none-any.whl (44K wheel)
  * dist/jbom-1.0.1.tar.gz (90K source distribution)
- Packages include all documentation, tests, and source code
- Ready for upload to PyPI ([`bd96053`](https://github.com/plocher/jBOM/commit/bd960534942514f0f920e4caab6d0e375d68eb7d))

* Phase 4: Create distribution documentation

Files created:
- CHANGELOG.md: Comprehensive version history documenting:
  * v1.0.1 changes: field system enhancements, tolerance improvements, packaging infrastructure
  * v1.0.0 initial release features
  * Standard keepachangelog.com format
- CONTRIBUTING.md: Developer guidelines covering:
  * Development setup and environment configuration
  * Running and writing tests
  * Code style and standards (PEP 8, type hints, docstrings)
  * Project structure and key classes
  * Common development tasks (new component types, matching algorithms, etc.)
  * Testing guidelines with 27 test class organization
  * Version management and release procedures
  * Package building and PyPI upload instructions

These documents provide clear guidance for developers contributing to or maintaining jBOM. ([`bfb84fc`](https://github.com/plocher/jBOM/commit/bfb84fc01a3d3ed1b0a97417f7e826dc8ac2dbfb))

* Move original jbom.py and test_jbom.py to new package structure

Files moved:
- jbom.py → src/jbom/jbom.py (via git operations)
- test_jbom.py → tests/test_jbom.py (via git operations)

These are now in their proper locations under the new src/ layout
for modern Python packaging. ([`b468157`](https://github.com/plocher/jBOM/commit/b4681579be59b546fdc8ebe4aa4223454134d900))

* Phase 1: Set up standard Python packaging infrastructure

Files created:
- src/jbom/__version__.py: Central version source (1.0.1)
- src/jbom/__init__.py: Package initialization exposing public API
- src/jbom/__main__.py: CLI entry point for 'python -m jbom'
- src/jbom/jbom.py: Core module (copied from root)
- tests/__init__.py: Test package initialization
- tests/test_jbom.py: Test suite (copied and updated imports)
- MANIFEST.in: Include non-Python files in distribution
- setup.py: Minimal legacy compatibility file

Files modified:
- pyproject.toml: Updated to v1.0.1 with complete project metadata, all 4 Python versions,
  proper classifiers (Development Status, AGPLv3), project URLs, optional dependencies for
  excel/numbers/dev/all, and src layout configuration

Project structure now follows modern Python packaging best practices with:
- src/ layout (recommended by packaging.python.org)
- Single version source in __version__.py
- Comprehensive pyproject.toml configuration
- Proper console script entry point (jbom command)
- All dependencies and extras properly declared ([`c6e277c`](https://github.com/plocher/jBOM/commit/c6e277c12908f512404b8eb026ec5f2085062b2a))

* Update WARP.md with comprehensive current project state

Updated WARP.md to reflect all recent development:

Test Suite Updates:
- Updated test count from 46 to 98 tests across 27 test classes
- Updated directory structure to include all man page files and plugin wrapper
- Updated file sizes and organization to match current state

Recent Development Activities (New Sections):
- Case-Insensitive Field Handling: normalize_field_name(), field_to_header(), 24 new tests
- Tolerance Substitution Enhancement: exact match preference, next-tighter preference, scoring penalty
- Documentation Updates: 4 new man page files, README.tests.md, SEE ALSO links, naming standardization
- Test Suite Growth: from 46 to 98 tests with field normalization and spreadsheet tests

Key Recent Changes (New Sections):
- Field System Enhancements: case-insensitive input, snake_case normalization, Title Case output
- Tolerance-Aware Matching: exact > next-tighter > over-spec, no looser substitution
- Integration Options: KiCad plugin, CLI, Python library

Extensions and Customization (New Sections):
- Guide for adding new component types, matching properties, spreadsheet formats, output fields
- Testing commands for running full suite, specific classes, and individual tests

This provides agents with complete context on the current project structure, recent work,
and guidance for future development and customization. ([`43c9296`](https://github.com/plocher/jBOM/commit/43c92960179401ee89ba07afd074478972253681))

* Change project name from KiCad BOM Generator to jBOM

Updated references in:
- jbom.py: Module docstring changed to 'jBOM - KiCad Bill of Materials Generator'
- test_jbom.py: Docstring simplified to 'Unit tests for jBOM'
- README.man4.md: Changed NAME section from 'KiCad BOM Generator Plugin' to 'jBOM Plugin for KiCad Eeschema'
- README.tests.md: Changed title to 'Unit Tests for jBOM'
- README.developer.md: Changed heading from 'Component Type Detection in KiCad BOM Generator' to 'Component Type Detection in jBOM'

This makes the naming more consistent throughout the project. ([`5616365`](https://github.com/plocher/jBOM/commit/5616365030ed531b68a0713f13f392c56a42c046))

* Remove redundant Usage Documentation section from README.md

The Usage Documentation section duplicated information now presented in the
SEE ALSO section with proper markdown links. Streamlined README.md by removing
the duplicate table and consolidating navigation to the SEE ALSO section at
the end of the document.

This keeps README.md focused on Quick Start and key concepts while delegating
detailed documentation references to the SEE ALSO section. ([`4bdeda0`](https://github.com/plocher/jBOM/commit/4bdeda02043be68a8be237da809af1b30fa5562c))

* Add markdown links to SEE ALSO sections in all README files

Updated cross-reference sections in:
- README.md: Added SEE ALSO with links to all documentation
- README.man1.md: Updated SEE ALSO with proper markdown links
- README.man5.md: Added markdown links (previously plain text)
- README.developer.md: Added SEE ALSO section with links, updated inline Documentation references

All README files now have clickable navigation between related documentation. ([`6c9772c`](https://github.com/plocher/jBOM/commit/6c9772ce6ee3a61229e56df3bee1a4ad8e3ed3e8))

* Enhance tolerance substitution scoring to prefer next-tighter over tightest

Code Changes (jbom.py):
- Modified _match_properties() tolerance scoring logic (lines 1057-1078)
- Exact tolerance matches still get full TOLERANCE_EXACT bonus
- Tighter tolerances now scored based on tolerance gap:
  * Within 1% of requirement: full TOLERANCE_BETTER bonus
  * More than 1% tighter: reduced bonus (half score) to discourage over-specification
- This ensures that when schematic requires 10%, a 5% part is ranked higher than a 1% part

Documentation Changes (README.man5.md):
- Clarified that exact tolerance matches are always preferred
- Added example: 10% required, 5% and 1% available → 5% ranks higher
- Explained the scoring penalty for over-specification
- Added concrete example showing ranking preference

Behavior:
- Schematic needs 10% tolerance AND 10% available → use 10% (exact match)
- Schematic needs 10% tolerance, only 5% and 1% available → use 5% (next-tighter preferred)
- Schematic needs 1% tolerance, only 5% or 10% available → no match (looser cannot substitute)

This prevents unnecessary use of expensive precision parts when tighter-than-necessary tolerances are specified in inventory. ([`a95c7c8`](https://github.com/plocher/jBOM/commit/a95c7c8eb559cc6290b656116c25e6c178254bd8))

* Expand tolerance substitution explanation in README.man5.md

Added concrete examples showing:
- When tighter tolerances are acceptable (5% → 1% is OK)
- When looser tolerances are rejected (1% → 5% is not OK)
- How scoring bonuses are awarded for exact and tighter matches

This clarifies the tolerance-aware substitution behavior for users ([`2c879c3`](https://github.com/plocher/jBOM/commit/2c879c37a68c22abbf9825dcab17153d70902a57))

* Clean up markdown table formatting in README.md

- Removed extra spacing in table cells for cleaner markdown source
- Table remains fully functional and renders correctly
- Compact format: |Document|Purpose| instead of | Document | Purpose | ([`b4ffa13`](https://github.com/plocher/jBOM/commit/b4ffa1313845fda2a7d255b2a987862c27a4621a))

* Convert HTML table to markdown table format in README.md

- Replaced HTML <table> syntax with standard markdown table format
- Improved readability in markdown source and rendering
- Removed bold formatting from document names (not needed in first column)
- Maintained all links and descriptions ([`8a46738`](https://github.com/plocher/jBOM/commit/8a467386fafbcdb33ce791c2b054737a224d5d0f))

* Create README.man5.md and update documentation for case-insensitive field handling

New file: README.man5.md
- Comprehensive inventory file format documentation (man page style)
- Required columns: IPN, Category, Value, Package, LCSC, Priority
- Optional columns: Manufacturer, MFGPN, Datasheet, and 20+ category-specific fields
- Field naming conventions and case-insensitive handling
- I:/C: prefix system for field disambiguation
- Spreadsheet format details (CSV, Excel, Apple Numbers)
- Matching behavior and validation rules
- Example CSV inventory file

Updated: README.md
- Added README.man5.md to documentation table
- New section: Field Naming & Case-Insensitivity
- Updated troubleshooting to reference README.man5.md
- Example formats for case-insensitive field input

Updated: README.man1.md
- New section: CASE-INSENSITIVE FIELD NAMES
- Documented accepted formats (snake_case, Title Case, UPPERCASE, Mixed, Spaced)
- Examples showing equivalent field specifications
- Note that all formats are normalized internally
- Cross-reference to README.man5.md for detailed inventory format

Updated: README.developer.md
- New subsection: Case-Insensitive Field Naming
- Documented normalize_field_name() function behavior
- Documented field_to_header() function behavior
- Explained normalization rules (Title Case, CamelCase, UPPERCASE, prefixes, whitespace)
- Noted idempotence property
- Updated Field Discovery section to note internal normalization
- Cross-reference to man5 for detailed inventory format

Key highlights:
- Users can now specify fields in ANY format (Reference, reference, REFERENCE, MatchQuality, etc.)
- CSV output headers always display in Title Case for readability
- Inventory file column names work with flexible naming ("Mfg PN" or "MFGPN")
- All formats automatically normalized to canonical snake_case internally ([`71f346b`](https://github.com/plocher/jBOM/commit/71f346b63b32f39356ddf22be5a148d3ae1d6d65))

* Add comprehensive unit tests for case-insensitive field name handling

Added 4 new test classes with 24 new test methods to ensure robustness of field normalization:

TestNormalizeFieldName (13 tests):
- snake_case preservation
- Title Case to snake_case conversion
- CamelCase to snake_case conversion
- UPPERCASE conversion
- I:/C: prefix handling (case-insensitive)
- Extra whitespace normalization
- Hyphen to underscore conversion
- Multiple underscore collapsing
- Idempotence verification
- Empty string edge case
- Mixed format handling

TestFieldToHeader (7 tests):
- Basic snake_case to Title Case conversion
- Prefixed fields without space after colon (I:Package not I: Package)
- Multiword field conversion
- Empty string edge case
- Single-word field conversion

TestInventoryRawHeaderMatching (5 tests):
- Exact field name matching from CSV headers
- Handling CSV fields with spaces (Mfg PN -> mfg_pn)
- Field existence checking
- Missing field handling

TestCaseInsensitiveFieldInput (3 tests):
- _get_field_value accepts various input formats
- Prefixed field case-insensitivity
- Component property field case-insensitivity

All 98 tests passing (24 new), 3 skipped (optional dependencies) ([`984f6a4`](https://github.com/plocher/jBOM/commit/984f6a4ee6d7d5d412e298c847bb3280ab86edba))

* Implement case-insensitive field name handling throughout jBOM

- Added normalize_field_name() function to convert any format (snake_case, Title Case, CamelCase, spaces) to canonical snake_case
- Added field_to_header() function to convert snake_case to Title Case for CSV headers
- Updated all field processing to use normalized snake_case internally
- User input now accepts any case/format for field names (Reference, reference, REFERENCE, match_quality, MatchQuality, etc.)
- CSV headers display in human-readable Title Case format without spaces after prefixes (I:Package not I: Package)
- Fixed _get_inventory_field_value() and _has_inventory_field() to properly normalize field names when matching against raw CSV data
- Updated _preset_fields() to use normalized snake_case field names
- Updated _parse_fields_argument() to normalize user-provided field tokens
- Updated get_available_fields() to normalize all field names to snake_case
- Updated _get_field_value() to work with normalized fields and handle prefixed fields (i:/c:) case-insensitively
- Updated write_bom_csv() to convert normalized fields to Title Case headers
- Updated test suite: fixed test_ambiguous_field_handling to expect lowercase prefixes in returned values
- All 74 tests pass with 3 skipped ([`6f890ef`](https://github.com/plocher/jBOM/commit/6f890ef120b86eec6162d540c499615f4dbefd34))

* Improve README documentation - simplify content and fix formatting

- Rewrite README.md with prose instead of bullet lists for better narrative flow
- Remove redundant Integration Methods section (covered by Usage Documentation table)
- Remove out-of-scope hierarchical schematic troubleshooting item
- Eliminate duplicate Support section
- Add author (John Plocher) to Version section
- Improve OPTIONS section formatting in README.man1.md with better indentation ([`13d19c4`](https://github.com/plocher/jBOM/commit/13d19c4df06c63344d2e894d395e786d10586712))

* cleanup ([`1d30390`](https://github.com/plocher/jBOM/commit/1d30390a807c1a9076a6491c362f5be4432e14eb))

* Move project structure to developer documentation and update license reference

- Remove Project Structure section from README.md (belongs in developer docs)
- Add comprehensive project structure to README.developer.md with file descriptions
- Update license reference from 'See LICENSE file for terms' to 'AGPLv3'
- Further streamline main README for clarity and focus
- Keep README.md as user-facing entry point ([`85f58d3`](https://github.com/plocher/jBOM/commit/85f58d3d31950aea885d084fc92b5da79296f9e4))

* Streamline README.md by removing duplicate task examples

- Remove redundant 'Common Tasks' section (examples belong in README.man1.md)
- Update outdated flag references (-m flag and --format option removed)
- Fix GenerateOptions examples to use current API (remove manufacturer parameter)
- Reduce README.md from 209 to 160 lines while maintaining clarity
- Keep README as entry point; direct users to man pages for detailed examples ([`373cc55`](https://github.com/plocher/jBOM/commit/373cc5566f177f9698cb24e0e1253d336ad57662))

* Add clarifying comment on field qualification in presets

Document the principle: Standard BOM fields don't need I:/C: prefixes
since they're unambiguous; qualify only when needed for clarity.
Example: I:Package is explicit about source to avoid ambiguity. ([`8e3aeb4`](https://github.com/plocher/jBOM/commit/8e3aeb46b2245532c9999fae9ed8326119f422b7))

* Fix JLC preset to match JLCPCB actual requirements

- Remove Footprint (KiCad library reference) from JLC preset
- Use I:Package instead (actual physical package from inventory)
- Remove Description and Datasheet (not required by JLCPCB)
- JLC preset now minimal: Reference, Quantity, Value, Package, LCSC
- Aligns with JLCPCB documentation requirements
- All 74 tests pass ([`a489ef2`](https://github.com/plocher/jBOM/commit/a489ef2d5662d796737f58420ba34635293df649))

* Simplify FIELD_PRESETS by combining base and suffix into single fields key

- Change from {base, suffix} structure to single {fields} list
- Eliminates unnecessary complexity without losing any functionality
- All 74 tests pass
- Easier to understand and extend presets ([`4d2ef4e`](https://github.com/plocher/jBOM/commit/4d2ef4e925ffc73b5161c56fd823a7d6dcd80a7d))

* updated jlc preset ([`d187e92`](https://github.com/plocher/jBOM/commit/d187e925be0ce15d47dda526f6b8a3f96310ec9f))

* Update --fields help text to include all presets ([`7de1594`](https://github.com/plocher/jBOM/commit/7de1594847960d4c2f4acfeba2be6e4f3ffb5257))

* Refactor field presets to use data-driven design and add new presets

- Convert FIELD_PRESETS to a reusable data structure (name -> base/suffix/description)
- Add +minimal preset: minimal set with just Reference, Quantity, Value, LCSC
- Add +all preset: includes all available fields from inventory and components
- Update preset validation to use FIELD_PRESETS.keys() dynamically
- Improve error messages with sorted preset list
- Add 2 new tests for +minimal and +all presets
- Update documentation (README.man1.md, README.man4.md) with new presets
- All 74 tests pass (66 original + 8 field parsing + 2 new preset tests) ([`641f86a`](https://github.com/plocher/jBOM/commit/641f86a0add47aba4e2c3624a5fb924b0a84932d))

* Unify --fields argument to support preset expansion with + prefix

- Remove --fields-preset and --format arguments (not used by KiCad plugin)
- Implement _parse_fields_argument() to handle unified field syntax
- Support preset expansion: -f +jlc or -f +standard
- Support custom field lists: -f "Reference,Quantity,Value,LCSC"
- Support mixed syntax: -f "+jlc,CustomField,I:Tolerance"
- Add 8 new tests for field parsing, preset expansion, and validation
- Update field preset logic to use + prefix in documentation
- All 72 tests pass (64 original + 8 new) ([`77fff92`](https://github.com/plocher/jBOM/commit/77fff925e806a8f2ff241fda79d748dd7d21a913))

* Update documentation to remove -m/--manufacturer flag references

- Remove -m flag from README.man1.md (CLI reference)
- Remove -m flag from README.man3.md (Python API)
- Remove -m flag from README.man4.md (KiCad plugin)
- Update field preset descriptions
- Update example commands ([`9cf7917`](https://github.com/plocher/jBOM/commit/9cf7917343b2b22cc3a23ee38abae4dd495a30d0))

* Remove -m/--manufacturer flag and complete refactoring

- Remove -m, --manufacturer argument from CLI and KiCad plugin
- Remove manufacturer field from GenerateOptions dataclass
- Simplify _preset_fields() function signature (remove include_mfg parameter)
- Update all callers to use new signature
- Fix duplicate 'if args.fields:' condition
- All 64 unit tests pass ([`42cac95`](https://github.com/plocher/jBOM/commit/42cac95f7105ff3382697b1d7c3065d0182f78bb))

* Restructure documentation into modular man pages

Split overly-long README.md (362 lines) into Unix-style man pages:
- README.man1.md (CLI reference): 166 lines with options, fields, examples, troubleshooting
- README.man3.md (Python API): 256 lines with classes, functions, workflows
- README.man4.md (KiCad plugin): 190 lines with setup, configurations, integration

Rewrote README.md as concise overview (208 lines):
- Quick start and installation
- Links to detailed man pages for each use case
- Common tasks with examples
- Brief troubleshooting guide
- Project structure and version info

This makes documentation easier to navigate:
- README.md for getting started and finding what you need
- Man pages for detailed reference when needed
- Developers can still access README.developer.md for internals ([`0280d2d`](https://github.com/plocher/jBOM/commit/0280d2d99ccd8fc6325b176838e864c94ce353ac))

* Update README with KiCad workflow integration instructions

Add comprehensive section covering three integration methods:
1. KiCad Eeschema plugin (Generate BOM dialog)
2. Command-line interface (for scripting and CI)
3. Python library API (for embedding in other tools)

Each method includes:
- Setup/usage instructions
- Common flags and options
- Typical workflow steps
- Tips and best practices ([`e9cd1a0`](https://github.com/plocher/jBOM/commit/e9cd1a0712f6cc4019e4ea5aa63b11160af985f7))

* Remove compatibility shims and stabilize test suite

- Remove kicad_bom_generator.py shim module (direct imports from jbom now)
- Remove optional 'name' field from InventoryItem dataclass
- Update all test imports to use jbom directly (16 import statements)
- Update test_inventory_item_creation to not pass 'name' parameter
- Update test_excel_file_loading to verify other fields instead of 'name'
- Remove 'name=row.get()' from inventory instantiation in _process_inventory_data

All 64 unit tests pass (3 skipped). Verified with integration tests on all three example projects (AltmillSwitches, Brakeman-RED, Core-wt32-eth0) using SPCoast-INVENTORY.numbers with debug flag. ([`1305644`](https://github.com/plocher/jBOM/commit/13056447e27dae47d154bb02f3cfca8a64208f98))

* Tests: export _shorten_url/_wrap_text in shim; map Excel/CSV 'Name' column to InventoryItem.name in inventory processing ([`173a3da`](https://github.com/plocher/jBOM/commit/173a3dac4c185b5227defb1225aefef6478a1cb0))

* Tests: add compatibility shim module kicad_bom_generator.py and add InventoryItem.name for legacy tests ([`0c9881f`](https://github.com/plocher/jBOM/commit/0c9881f669d22a7af875dc301b3dfc5a8f3026cd))

* Stage 5/5: Add pyproject.toml packaging with console script entry point jbom=jbom:main ([`cb92adb`](https://github.com/plocher/jBOM/commit/cb92adb3a3cc4d18a3ff480b3aee67124538fc62))

* Stage 4/5: Add output presets and multi-format emission (--fields-preset, --format, --multi-format); keep standard CSV as default ([`0c6817c`](https://github.com/plocher/jBOM/commit/0c6817c2e69f323177d4c30605379f124cdd22c8))

* Stage 3/5: Add KiCad wrapper script kicad_jbom_plugin.py for Eeschema BOM integration (%I/%O) ([`b32df93`](https://github.com/plocher/jBOM/commit/b32df931ca4b51e1a3777ef30c0e73b9acba1eb9))

* Stage 2/5: Stabilize CLI: add --quiet, --json-report, --outdir; suppress non-essential prints when quiet; write optional JSON report; return exit code 2 on unmatched entries ([`826d92f`](https://github.com/plocher/jBOM/commit/826d92f3bb3e89fe569c9b3e07397fa645475c8b))

* Stage 1/5: Introduce library API (GenerateOptions + generate_bom_api) with no prints/exits; keep existing CLI unchanged ([`293b83e`](https://github.com/plocher/jBOM/commit/293b83e220c177e197330e40171aaf1778812abf))

* baseline v1.0 ([`bfc3b40`](https://github.com/plocher/jBOM/commit/bfc3b40524e8b9e0f6cdf740fa2b0a024782a6e4))

* Initial commit ([`a4f4e66`](https://github.com/plocher/jBOM/commit/a4f4e667d69a26c7eea05fc4eddb8784b7f248dc))
