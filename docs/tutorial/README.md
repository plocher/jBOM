# jBOM Tutorial Series

Welcome to jBOM. These tutorials walk you through real workflows, starting from nothing and working up to customizing jBOM for your team or fab house.

Each tutorial builds on the previous one. Start at the beginning if you are new to jBOM.

## Tutorial Path

### [1. Key Concepts](README.context.md)
**5 minutes — read first**

Learn the mental model behind jBOM before you type any commands:
- What problem jBOM solves and why it works the way it does
- The three things you need: a KiCad project, an inventory file, and a fabricator profile
- How profiles let you change behaviour without changing your design

### [2. Your First BOM](README.implementation.md)
**15 minutes — core workflow**

Go from a KiCad project to JLCPCB-ready manufacturing files:
- Extract an inventory template from your schematic
- Fill in part numbers and edit your inventory
- Generate a fabrication BOM and a component placement file (CPL)
- Check what matched and what didn't

### [3. Finding and Enriching Parts](README.integration.md)
**20 minutes — search and bulk enrichment**

Find supplier part numbers without leaving the terminal:
- Search Mouser interactively with `jbom search`
- Bulk-match an entire inventory file against LCSC with `jbom inventory-search`
- Use a dry run to preview what will be searched before spending API quota
- Save an enriched inventory for BOM generation

### [4. Customising for Your Workflow](README.documentation.md)
**20 minutes — profiles and configuration**

Tailor jBOM's output and behaviour to your team or organisation:
- Use a custom fabricator profile with your own BOM column names
- Create a defaults profile that sets organisation-wide tolerances and voltage ratings
- Share profiles across a team using `JBOM_PROFILE_PATH`
- Override just what you need with `extends:`

## Quick Reference

Once you have worked through the tutorials, the complete command reference is in [README.man1.md](../README.man1.md).

For configuration details — profile file format, search paths, environment variables — see [README.configuration.md](../README.configuration.md).
