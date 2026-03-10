# Tutorial 3: Finding and Enriching Parts

In Tutorial 2 you filled in supplier part numbers by hand. For a new project with dozens of passives, that gets tedious fast. This tutorial covers three jBOM workflows for finding and maintaining supplier part numbers:

- `jbom search` — interactive search for a single part
- `jbom inventory --supplier` — auto-populate supplier PNs when generating your inventory
- `jbom audit --supplier` — detect stale or sub-optimal supplier PNs in an existing inventory

## Prerequisites

- An inventory CSV from Tutorial 2 (some supplier fields may be empty)
- A Mouser API key **or** use the built-in `generic` provider for offline testing

> **API keys**: `jbom search` defaults to Mouser. Get a free key at [mouser.com/api](https://www.mouser.com/api-hub/). The `generic` supplier is always available without any credentials and uses local fixture data — useful for testing your workflow before spending API quota.

## Step 1: Search for a single part interactively

```bash
export MOUSER_API_KEY=your_key_here
jbom search "10k 0603 resistor" --limit 5
```

This queries Mouser and prints a table of up to 5 matching parts:

```
Manufacturer  MPN              Description                 Stock   Price
-----------   ---------------  --------------------------  ------  -----
YAGEO         RC0603FR-0710KL  10 kOhms ±1% 0603 Thick..  847200  0.004
...
```

By default jBOM applies smart parametric filtering: it parses `"10k 0603 resistor"` and adds attribute filters for resistance, package, and tolerance. Disable this with `--no-parametric` if you want raw keyword results.

**Filter to a specific provider:**
```bash
jbom search "100nF 0603 X7R" --provider lcsc --limit 10
```

**See all available fields:**
```bash
jbom search "AMS1117-3.3" --list-fields
jbom search "AMS1117-3.3" --fields Mfr_Part_No,Description,Stock,Price_USD,LCSC
```

**Save results to CSV:**
```bash
jbom search "10k 0603 resistor" -o results.csv
```

## Step 2: Set up your API key permanently

Instead of `export` every session, add the key to your shell profile:

```bash
# ~/.zshrc or ~/.bashrc
export MOUSER_API_KEY=your_key_here
```

Or use a `.env` file in your project directory (with a tool like `direnv`).

---

## Step 3: Auto-populate supplier PNs at inventory-generation time

When you generate a new inventory, you can have jBOM immediately search for supplier part numbers for each component:

```bash
jbom inventory MyBoard/ --supplier mouser -o inventory.csv
```

This runs the standard inventory extraction, then for each row that does not already have a `Supplier` and `SPN` set, it searches the named supplier and fills in the top result.

**Output example** — the `Supplier` and `SPN` columns are populated where a match was found:

```
IPN,Category,Value,Package,Supplier,SPN,...
R-10K-0603,RES,10K,0603,mouser,71-RC0603FR-0710KL,...
R-100R-0402,RES,100R,0402,mouser,71-RC0402JR-07100RL,...
C-100NF-0603,CAP,100nF,0603,,,...
```

- Rows where the supplier found a match get `Supplier` and `SPN` filled in.
- Rows with no match (e.g. exotic connectors, custom ICs) are left blank for you to fill manually.
- Rows that already have a `Supplier` or `SPN` value are **never overwritten**.

**Dry-run first** — see what would be searched without making API calls:
```bash
jbom inventory MyBoard/ --supplier mouser --dry-run
```

**Use the generic provider** (offline, no API key needed — useful for testing):
```bash
jbom inventory MyBoard/ --supplier generic -o inventory.csv
```

---

## Step 4: Review the populated inventory

Open `inventory.csv`. For rows where jBOM found exactly one good candidate, the `Supplier` and `SPN` columns are filled. For rows with no match, search manually:

```bash
jbom search "AMS1117-3.3 SOT-223" --limit 5
```

Copy the best result's part number into the `SPN` column and set `Supplier` to the provider name (e.g. `mouser`).

Once you are happy with the inventory, use it to generate a BOM:
```bash
jbom bom MyBoard/ --jlc --inventory inventory.csv
```

---

## Step 5: Audit existing supplier PNs for staleness

Over time, supplier part numbers go out of stock, get superseded, or better alternatives become available. `jbom audit` can check your existing inventory against a live supplier catalog:

```bash
jbom audit inventory.csv --supplier mouser -o freshness_report.csv
```

**What it checks** (for each `ITEM` row with a `Supplier` and `SPN`):

| Outcome | Meaning |
|---------|---------|
| `STALE_PART / WARN` | The recorded PN was not found in a fresh search — may be discontinued or delisted |
| `BETTER_AVAILABLE / WARN` | A fresh search found a different PN that ranks higher (better stock/price) |
| Silent | The recorded PN is still the best result — no action needed |

**Review the report:**
```bash
# Show only rows that need attention
grep "STALE_PART\|BETTER_AVAILABLE" freshness_report.csv
```

For each `STALE_PART` or `BETTER_AVAILABLE` row, update `SPN` in your inventory to the suggested replacement. Re-run `jbom audit` after updating to confirm the issues are resolved.

**Use the generic provider** (offline testing without API calls):
```bash
jbom audit inventory.csv --supplier generic -o report.csv
```

---

## Step 6: Cache management

jBOM caches API responses on disk to avoid redundant calls. The cache is per-provider.

```bash
# Skip cache for this run (always fetch fresh data)
jbom inventory MyBoard/ --supplier mouser --no-cache -o inventory.csv

# Clear the cache before running
jbom inventory MyBoard/ --supplier mouser --clear-cache -o inventory.csv
```

Same flags work for `jbom audit`:
```bash
jbom audit inventory.csv --supplier mouser --no-cache -o report.csv
```

## Common issues

**"Search commands require API key"**: Set `MOUSER_API_KEY` environment variable or pass `--api-key YOUR_KEY`. Alternatively, use `--supplier generic` which never requires credentials.

**"Unsupported inventory file format"**: Install the optional parser:
```bash
pip install jbom[excel]    # for .xlsx / .xls
pip install jbom[numbers]  # for .numbers
```

**Low match quality**: The search uses smart parametric matching. If results are poor, check that your inventory `Value` and `Package` fields use standard conventions (e.g., `10K` not `10000`, `0603` not `0603_1608Metric`).

**Rows not being searched**: Only `ITEM` rows in recognised categories (RES, CAP, IND, etc.) are searched. Use `--dry-run` to see exactly which rows would be searched.

## Next steps

- [Tutorial 4: Customising for Your Workflow](README.documentation.md) — create a custom fabricator profile, set org-wide tolerances with a defaults profile
