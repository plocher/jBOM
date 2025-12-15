# CHANGELOG

<!-- version list -->

## v2.1.0 (2025-12-15)

### Documentation

- Add detailed implementation notes for Steps 5-6 (generator refactoring)
  ([`6a7d730`](https://github.com/plocher/jBOM/commit/6a7d730a93fb9e634ec4d6faeb8aeb4254e4cf78))

- Add structural cleanup analysis
  ([`44587df`](https://github.com/plocher/jBOM/commit/44587df53fd0b55ce82a3c47a32f4dbe78e5ab8b))

- Enhance documentation for BOM and PCB placement features
  ([`ede97cb`](https://github.com/plocher/jBOM/commit/ede97cb7349d7640ba5ac332d2f807b37b8ccd3c))

### Features

- Add auto-detection of PCB files for pos command
  ([`ba56527`](https://github.com/plocher/jBOM/commit/ba56527d178433800b695f232961797858a77de9))

### Refactoring

- Add generator infrastructure Phase 1 - common abstractions
  ([`56b606f`](https://github.com/plocher/jBOM/commit/56b606feb64eb01ae490dc9ac164774067bc5564))

- Consolidate file discovery functions in common.utils
  ([`99f7672`](https://github.com/plocher/jBOM/commit/99f76723ce3270a3512241004efd2e13c79331f5))

- Simplify CLI using shared utilities (Phase 3)
  ([`74a1419`](https://github.com/plocher/jBOM/commit/74a1419dbd969d49125fc59484fa59c8032b430d))


## v2.0.0 (2025-12-15)

### Build System

- Add Makefile for developer workflows
  ([`b60284d`](https://github.com/plocher/jBOM/commit/b60284dbf89b2e476ffaded5a23f040f47ed1c26))

### Chores

- Apply pre-commit formatting fixes
  ([`491e165`](https://github.com/plocher/jBOM/commit/491e16544bf8bcc04f6c5d525959e9570f3ac6eb))

### Documentation

- Update documentation for new architecture and CLI
  ([`6976709`](https://github.com/plocher/jBOM/commit/69767093a58b214cc6527669a8d195b8c72f465d))

### Features

- Add PCB board loading with pcbnew API and S-expression fallback
  ([`e8f56ca`](https://github.com/plocher/jBOM/commit/e8f56ca36f12e71a967b8e448aa439c879b3ce7e))

- Replace CLI with subcommand-based interface
  ([`1f6e3eb`](https://github.com/plocher/jBOM/commit/1f6e3eba7a99b4853f695cfa5edf4f049603a961))

### Refactoring

- Restructure codebase into modular package hierarchy
  ([`8ce30ee`](https://github.com/plocher/jBOM/commit/8ce30eeaf00f7f1d8671c7648ef5387f04643352))

### Testing

- Add comprehensive unit, CLI, and integration tests
  ([`caa38b9`](https://github.com/plocher/jBOM/commit/caa38b932737a4e7e2401d5c2e19d807e5c44315))

### Breaking Changes

- Internal package structure reorganized


## v1.0.2 (2025-12-14)

- Initial Release
