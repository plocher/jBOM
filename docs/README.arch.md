# jBOM Architecture (Dec 2025)
This document summarizes the current high-level module layout to support upcoming PCB integration while maintaining backward compatibility.

## Packages
- `jbom.jbom` — existing implementation (schematic parsing, inventory matcher, BOM generator, CLI). Still the source of truth.
- `jbom.sch` — schematic-focused API surface that re-exports from `jbom.jbom`:
  - `jbom.sch.api` → `GenerateOptions`, `generate_bom_api`
  - `jbom.sch.model` → `Component`
  - `jbom.sch.parser` → `KiCadParser`
  - `jbom.sch.bom` → `BOMEntry`, `BOMGenerator`
- `jbom.common` — shared helpers (for both schematic and future PCB code):
  - `fields` (normalize names), `types` (enums/constants), `packages` (package lists)
  - `values` (numeric parsers/formatters for RES/CAP/IND)
  - `utils` (placeholder for future file-discovery/natsort helpers)
- `jbom.inventory` — inventory loader/matcher API surface (re-exports for now)
- `jbom.pcb` — placeholder for upcoming PCB integration modules (`board_loader`, `model`, `position`, `check`).

## Compatibility
- Public imports documented previously continue to work (e.g., `from jbom import generate_bom_api`).
- Tests and the KiCad Eeschema wrapper remain unchanged.
- New imports (optional now): `from jbom.sch import GenerateOptions, generate_bom_api`.

## Next steps
- Extract more shared utilities from `jbom.jbom` into `jbom.common` incrementally, keeping tests green.
- Implement `jbom.pcb` modules and a Pcbnew Action Plugin that consumes the shared helpers.
