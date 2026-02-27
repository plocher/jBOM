# Planning: Fabrication Integration & Tool Consolidation

## Overview
jBOM currently excels at Inventory Management and BOM/POS generation (the "Data" layer). However, it stops short of the full "Fabrication" layer (Gerbers + Zipping for upload). Tools like `kicad-jlcpcb-tools` provide a "One Click" fabrication experience but lack jBOM's sophisticated inventory federation and matching logic.

This document outlines the investigation into bridging this gap, potentially evolving jBOM into a complete Fabrication Automation Platform.

## Goals
1.  **Unified Workflow**: A single command/action that takes a Project + Inventory and produces a ready-to-upload Fabrication Zip (Gerbers + BOM + CPL).
2.  **Leverage Existing Art**: Evaluate `kicad-jlcpcb-tools` to avoid reinventing Gerber generation logic.
3.  **Database Integration**: Determine if integrating with `kicad-jlcpcb-tools` (or forking it) provides the "Offline Part Search" capability needed for jBOM Step 5.

## Investigation Paths

### Path A: Co-existence / Integration
*   **Concept**: User runs `jbom` to prepare data, then `kicad-jlcpcb-tools` to package it.
*   **Challenge**: `kicad-jlcpcb-tools` has its own BOM logic. Can we override it?
*   **Task**: Check if `kicad-jlcpcb-tools` accepts a pre-generated BOM CSV or if we can inject one.

### Path B: Extension (PR to upstream)
*   **Concept**: Submit PR to `kicad-jlcpcb-tools` to allow "External BOM Generator" plugin.
*   **Task**: Analyze `kicad-jlcpcb-tools` plugin architecture. Is it extensible?

### Path C: Absorption / Fork (`jbom fab` command)
*   **Concept**: Port the Gerber/Zip logic from `kicad-jlcpcb-tools` into `jBOM` (or a new `jbom-fab` plugin).
*   **Task**: Identify dependencies for Gerber generation.
    *   Does it use `kicad-cli`? (Available in v7/v8).
    *   Does it use Python `pcbnew` PlotController? (Complex).
*   **Benefit**: If we absorb this, we also absorb their "Parts Database" logic, solving Step 5 (Offline Search) natively.

## Plan

### 1. Code Analysis of `kicad-jlcpcb-tools`
- [ ] Clone repo (already done/available).
- [ ] Identify `Gerber` generation logic file.
- [ ] Identify `BOM` generation logic file.
- [ ] Identify `Database/Search` logic file.

### 2. Prototype `jbom fab`
- [ ] Experiment with `kicad-cli pcb export gerbers` and `kicad-cli pcb export drill`.
- [ ] If `kicad-cli` is sufficient, Path C is very attractive (clean dependency).

### 3. Decision
- **Recommendation**: Path A (Co-existence) for now, evolving into Path C (Absorption) with a Dual-Backend Strategy.
- **Dual-Backend Strategy**:
    - The `jBOM` Foundation API must support both "In-Process" (pcbnew) and "Out-of-Process" (kicad-cli) execution.
    - `FabricationBackend` interface with `PcbnewBackend` and `KicadCliBackend` implementations.
    - This allows `jBOM` to be a "Universal Fab Tool" working in both CLI and Plugin contexts.

## Implications for Step 5 (Search DB)
- **Catalog Integration**: Step 5 should implement the "Offline Search" by adopting the SQLite DB format used by `kicad-jlcpcb-tools`.
- This database becomes a "Catalog Source" for `jBOM`'s federated inventory system.
