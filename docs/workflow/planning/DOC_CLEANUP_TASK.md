# Documentation Cleanup Task

**Purpose**: Training exercise for multi-agent collaboration patterns

## Current State

### Root Level (`jbom-new/`)
- ❓ KICAD_FILE_FORMAT_ISSUE.md - Technical note about KiCad parsing
- ❓ ISSUE-43-user-defined-config-files.md - Design discussion
- ✅ CHANGELOG.md - Important (keep)
- ❓ REFACTORING_SUMMARY.md - Historical context about jbom-new creation
- ✅ NEXT.md - **Active tracking** (keep, maybe move to docs/)
- ✅ README.md - **Essential** (keep)
- ❓ IMPROVED_PROJECT_PATTERNS.md - Design notes
- ❓ FABRICATOR_FIELDS_GAP_ANALYSIS.md - Work-in-progress analysis
- ✅ QUICK_START.md - **Active tracking** (keep, maybe move to docs/)

### Docs Directory (`jbom-new/docs/`)

**Architecture** (Well-organized, keep):
- architecture/README.md
- architecture/design-patterns.md
- architecture/domain-centric-design.md
- architecture/integration-patterns.md
- architecture/layer-responsibilities.md
- architecture/testing.md

**Tutorial** (Well-organized, keep):
- tutorial/README.md
- tutorial/README.context.md
- tutorial/README.documentation.md
- tutorial/README.implementation.md
- tutorial/README.integration.md

**Migration** (Historical):
- migration/project_centric_migration.md

**Guides** (Current):
- ✅ USER_GUIDE.md
- ✅ DEVELOPER_GUIDE.md
- ✅ GIT_WORKFLOW.md (just created)
- ✅ HUMAN_WORKFLOW.md (just created)
- ✅ PHASE_1_TASKS.md (just created)
- ✅ WORK_LOG.md (just created)

**Root**:
- README.md - Index to other docs

## Problems Identified

1. **Inconsistent Location**: Active tracking docs (NEXT.md, QUICK_START.md) in root vs docs/
2. **Work-In-Progress Clutter**: ISSUE-43, FABRICATOR_FIELDS_GAP_ANALYSIS in root
3. **Historical Context Mixed**: REFACTORING_SUMMARY might be valuable but clutters root
4. **Unclear Status**: Which docs are "notes" vs "current" vs "completed"?

## Proposed Structure

```
jbom-new/
├── README.md                    # Main entry point
├── CHANGELOG.md                 # Release history
│
├── docs/
│   ├── README.md                # Docs index
│   │
│   ├── architecture/            # Design patterns (keep as-is, add new arch and design decisions as they are made)
│   │   ├── README.md
│   │   ├── design-patterns.md
│   │   └── ...
│   │
│   ├── tutorial/                # Implementation guides (keep as-is)
│   │   └── ...
│   │
│   ├── guides/                  # NEW: User-facing guides
│   │   ├── USER_GUIDE.md       # Moved from docs/
│   │   └── DEVELOPER_GUIDE.md  # Moved from docs/
│   │
│   ├── workflow/                # NEW: Active tracking for work in progress
│   │   ├── NEXT.md              # Current task (moved from root)
│   │   ├── QUICK_START.md       # Quick ref (moved from root)
│   │   ├── WORK_LOG.md          # Session log
│   │   ├── GIT_WORKFLOW.md      # Git patterns
│   │   ├── HUMAN_WORKFLOW.md    # Paired development guide
│   │   │
│   │   ├── planning/            # NEW: Phase planning
│   │   │   └── PHASE_1_TASKS.md # Moved from docs/
│   │   │
│   │   ├── completed/           # NEW: Completed work archive
│   │   │   └── README.md        # With PR/Issue links
│   │   │
│   │   └── WIP/                 # NEW: Work-in-progress notes
│   │       └── ISSUE-43-user-defined-config-files.md
│
├── features/                    # BDD Gherkin feature tests (archived)
│   ├── GHERKIN_RECIPE.md        # ← merge IMPROVED_PROJECT_PATTERNS here
│   └── ...

```

## Task Breakdown for Agent Delegation

### Phase 0: Your Decision (5 minutes)
**What YOU do**:
1. Review this structure
2. Approve/reject/modify the organization
3. Decide which docs are "notes" vs "completed" vs "active"
4. Give clear guidance on ambiguous files

**Deliverable**: Approved structure + classification decisions

---

### Task DC-1: Create Directory Structure (Agent, 5 min)
**What Agent Does**:
- Create new directories: docs/guides/, docs/workflow/planning/, docs/workflow/completed/, docs/workflow/WIP/
- Create stub README.md files explaining each directory

**Success Criteria**:
- [ ] Directories exist
- [ ] Each has README.md explaining purpose
- [ ] No files moved yet (just structure)

**Handoff**: Directory structure ready for file moves

---

### Task DC-2: Move Active Tracking Docs (Agent, 5 min)
**What Agent Does**:
- Move: NEXT.md → docs/workflow/
- Move: QUICK_START.md → docs/workflow/
- Update any references to these files in other docs
- Update .gitignore if needed

**Success Criteria**:
- [ ] Files moved
- [ ] All references updated (grep to verify)
- [ ] Files still readable at new location

**Handoff**: Active tracking in docs/workflow/

---

### Task DC-3: Reorganize User/Dev Guides (Agent, 5 min)
**What Agent Does**:
- Move: docs/USER_GUIDE.md → docs/guides/
- Move: docs/DEVELOPER_GUIDE.md → docs/guides/
- Update docs/README.md to reflect new structure

**Success Criteria**:
- [ ] Guides moved
- [ ] docs/README.md updated with new paths
- [ ] Links still work

**Handoff**: Guides organized

---

### Task DC-4: Move Planning Docs (Agent, 5 min)
**What Agent Does**:
- Move: docs/PHASE_1_TASKS.md → docs/workflow/planning/
- Update references in NEXT.md, HUMAN_WORKFLOW.md

**Success Criteria**:
- [ ] Planning doc moved
- [ ] References updated
- [ ] HUMAN_WORKFLOW instructions still accurate

**Handoff**: Planning docs separate

---

### Task DC-5: Move Architectural Decision Docs (Agent, 10 min)
**What Agent Does**:
- Move: REFACTORING_SUMMARY.md → docs/architecture/why-jbom-new.md
- Move: docs/migration/project_centric_migration.md → docs/architecture/project-centric-design.md
- Update docs/architecture/README.md to list these new docs with context
- Add creation dates and related PRs/Issues to each
- Create docs/workflow/completed/README.md (empty for now, explains purpose)

**Success Criteria**:
- [ ] Architectural docs moved to architecture/
- [ ] architecture/README.md updated with new entries
- [ ] Context preserved (dates, issues)
- [ ] completed/ directory exists with README

**Handoff**: History preserved but not cluttering

---

### Task DC-6: Handle WIP and Cleanup Notes (Agent, 15 min)
**What Agent Does**:
- Move: ISSUE-43-user-defined-config-files.md → docs/workflow/WIP/
- Delete: KICAD_FILE_FORMAT_ISSUE.md (decision made: not pursuing that path)
- Create GitHub Issue for FABRICATOR_FIELDS_GAP_ANALYSIS.md, then delete file
- Move: IMPROVED_PROJECT_PATTERNS.md → features/ (will merge with GHERKIN_RECIPE.md in DC-6b)
- Create docs/workflow/WIP/README.md explaining active investigations
- Add note in requirements/1-Functional-Scenarios.md pointing to ISSUE-43 in WIP/

**GitHub Issue Template** (for FABRICATOR_FIELDS_GAP_ANALYSIS):
```
Title: Research: Fabricator field system completeness

Context: Early analysis in FABRICATOR_FIELDS_GAP_ANALYSIS.md identified
potential gaps in fabricator field customization.

Task: Review analysis and determine if additional work needed after
Phase 1 sophisticated matcher is complete.

Reference: See deleted file in git history at [commit hash]
Related: Issue #42 (fabricator field system)
```

**Success Criteria**:
- [ ] ISSUE-43 in docs/workflow/WIP/
- [ ] KICAD_FILE_FORMAT_ISSUE deleted
- [ ] GitHub issue created for FABRICATOR analysis
- [ ] FABRICATOR doc deleted after issue created
- [ ] IMPROVED_PROJECT_PATTERNS moved to features/
- [ ] WIP/README.md created
- [ ] Cross-reference added to requirements/

**Handoff**: WIP organized, obsolete docs cleaned up

---

### Task DC-6b: Merge Project Patterns into Gherkin Recipe (Agent, 10 min)
**What Agent Does**:
- Read both: features/IMPROVED_PROJECT_PATTERNS.md and features/GHERKIN_RECIPE.md
- Identify overlapping vs unique content
- Merge IMPROVED_PROJECT_PATTERNS content into GHERKIN_RECIPE.md
- Delete IMPROVED_PROJECT_PATTERNS.md after merge
- Update features/ documentation references if needed

**Success Criteria**:
- [ ] Content merged without duplication
- [ ] IMPROVED_PROJECT_PATTERNS deleted
- [ ] GHERKIN_RECIPE.md is comprehensive
- [ ] No broken references

**Handoff**: Feature test documentation consolidated

---

### Task DC-7: Update Main README and Index (Agent, 15 min)
**What Agent Does**:
- Update jbom-new/README.md with new doc structure
- Update docs/README.md as comprehensive index
- Add navigation links between related docs
- Ensure all references are correct

**Success Criteria**:
- [ ] README.md reflects new structure
- [ ] docs/README.md is useful index
- [ ] No broken links (test with markdown checker)
- [ ] Clear entry points for different user needs

**Handoff**: Documentation navigable

---

### Task DC-8: Validate and Commit (Agent, 10 min)
**What Agent Does**:
- Run: `find jbom-new -name "*.md" -type f` - verify nothing lost
- Check: All markdown files are in expected locations
- Verify: No broken internal links
- Commit with detailed message listing moves

**Success Criteria**:
- [ ] All files accounted for
- [ ] No broken references
- [ ] Clean commit showing file moves
- [ ] Co-authored by Warp

**Deliverable**: Clean, organized documentation structure

---

## Multi-Agent Collaboration Pattern

### Your Role in Each Task
1. **Review the task definition** - Do you agree with approach?
2. **Watch agent work** - Does it follow the task?
3. **Course-correct if needed** - Agent going off track?
4. **Approve output** - Ready to commit?
5. **Update tracking** - Mark task done, note learnings

### Agent Handoff Pattern
Each task produces:
- **Files changed** (git status)
- **Brief summary** (what was done)
- **Next task ready** (or blocker identified)

### Time Boxing
- Each task: 5-15 minutes
- If task takes longer: Stop, break it down further
- If blocked: Document blocker, move to next task

### Learning Checkpoints
After every 2-3 tasks, you pause and reflect:
- What worked well?
- What needed correction?
- Any pattern emerging?
- Adjust approach for remaining tasks?

---

## Next Step: YOUR Decision

**Before starting Task DC-1, you need to decide**:

1. **Approve this structure?** Or modify it?

2. **File Classifications** (APPROVED):
   - ✅ REFACTORING_SUMMARY.md → docs/architecture/why-jbom-new.md (architectural decision)
   - ✅ KICAD_FILE_FORMAT_ISSUE.md → DELETE (decision made: not pursuing)
   - ✅ ISSUE-43-user-defined-config-files.md → docs/workflow/WIP/ (link from requirements)
   - ✅ IMPROVED_PROJECT_PATTERNS.md → Merge into features/GHERKIN_RECIPE.md
   - ✅ FABRICATOR_FIELDS_GAP_ANALYSIS.md → GitHub issue, then DELETE

3. **Files to DELETE**:
   - ✅ KICAD_FILE_FORMAT_ISSUE.md (after noting decision)
   - ✅ FABRICATOR_FIELDS_GAP_ANALYSIS.md (after creating GitHub issue)
   - ✅ IMPROVED_PROJECT_PATTERNS.md (after merging to GHERKIN_RECIPE)

4. **Ready to delegate Task DC-1** to an agent?
   - ✅ YES - Structure approved, decisions made

---

## Success Criteria for Overall Task

- [ ] Documentation structure is logical and navigable
- [ ] Active tracking docs (NEXT.md, QUICK_START.md) are easily found
- [ ] Historical context preserved but not cluttering
- [ ] WIP notes clearly marked as such
- [ ] No broken references between docs
- [ ] You learned how to delegate bounded tasks to agents
- [ ] Pattern documented for Phase 1 work
