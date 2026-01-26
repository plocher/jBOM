# Inventory Domain

## Use Case
As a hardware engineer, I want to understand what components I need and what I already have, so I can make informed decisions about ordering parts for manufacturing.

## Core User Needs
1. "I want to see all the components my project needs in a format I can use for ordering"
2. "I want to know which components from my project I don't already have in inventory"
3. "I want to add my project's components to my existing inventory without creating duplicates"
4. "I want to check against multiple inventory sources (suppliers, locations) with clear precedence"
5. "I want the system to handle missing or bad inventory files gracefully"

## Feature Files

### core.feature
Tests basic inventory generation from KiCad projects.
- Scenarios: generate IPNs, categorize components, normalize packaging
- Covers user need #1

### inventory_matching.feature
Tests matching project components against existing inventory.
- Scenarios: basic matching, filtering, error handling for missing files
- Covers user needs #2, #3, #5

### IPN_generation.feature
Tests IPN creation logic and formatting consistency.
- Scenarios: category detection, value normalization, IPN patterns
- Supports all user needs through stable component identification

### multi_source.feature
Tests multiple inventory file handling with precedence.
- Scenarios: precedence rules, duplicate handling, partial matches
- Covers user need #4

### multi_source_edge_cases.feature
Tests complex scenarios with malformed files and error conditions.
- Scenarios: missing files, malformed CSV, duplicate IPNs
- Covers user need #5

### file_safety.feature
Tests file handling and command validation.
- Scenarios: file permissions, invalid combinations
- Covers user need #5

## Implementation Notes
- All features use CSV-first assertions with `jbom inventory -o -` for reliable data validation
- Tests focus on business outcomes (what components are identified) rather than console formatting
- Error scenarios verify both exit codes and meaningful error messages
