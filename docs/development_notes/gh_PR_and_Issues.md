# GitHub PR and Issues: zsh-safe authoring with gh

Problem
Literal `\n` showed up in PR/Issue bodies when passing text via `gh` with shell-quoted newlines. zsh quoting plus `gh` CLI can easily mangle multi-line bodies.

Recommendation
Always put Markdown in a file and use `--body-file`/`--message-file` with `gh`.

PRs
```bash
# Create or edit a PR with a body file
cat > /tmp/pr-body.md <<'EOF'
feat: project-centric architecture core services + CLI integration (Issue #24)

What's in this PR
- New services: ProjectDiscovery, ProjectContext, ProjectFileResolver, CLI discovery helpers
- Updated CLIs: bom, pos, inventory support project-centric inputs
- Hierarchical schematic processing and cross-command intelligence (BOM↔PCB, POS↔SCH)
- Unit tests for core services

Related
- Regression suite PR: #28
- Follow-up expansion issue: #27

Closes #24
EOF

gh pr create \
  --title "feat: project-centric architecture core services + CLI integration (Issue #24)" \
  --body-file /tmp/pr-body.md \
  --base main --head feature/issue-24-project-centric-implementation

# To update an existing PR body later
gh pr edit 29 --body-file /tmp/pr-body.md
```

Issues
```bash
cat > /tmp/issue-body.md <<'EOF'
Expand project-centric architecture coverage and regression/feature tests across all commands

Scope
- Ensure inventory subcommands (and others) follow discovery and cross-file rules like BOM/POS
- Add regression + feature tests per features/regression/README.md
- Validate base-name and directory inputs across all commands
- Verify legacy .pro discovery and hierarchical schematic handling

Acceptance Criteria
- All commands accept project directory, base name, and explicit file paths with cross-resolution intelligence
- Regression suite updated; new behavior has feature tests
- Backward compatibility preserved

Relationship
- Related to #24; follow-up expansion.
EOF

gh issue create --title "Expand project-centric architecture coverage and tests" --body-file /tmp/issue-body.md --label enhancement

# Edit an existing issue body
gh issue edit 27 --body-file /tmp/issue-body.md
```

Comments
```bash
# Create comment
cat > /tmp/comment.md <<'EOF'
Project-Centric Architecture implemented and initial regression coverage added.

What was done
- Project-centric discovery across BOM, POS, inventory
- Cross-command intelligence: BOM accepts .kicad_pcb, POS accepts .kicad_sch
- Hierarchical schematic processing
- Backward-compatible explicit-file workflows
- Regression suite: features/regression/issue-24-project-centric-architecture.feature

Follow-ups
- Sub-issue #27 expands scope and adds comprehensive tests.
EOF

gh issue comment 24 --body-file /tmp/comment.md

# Edit a prior comment (requires comment ID)
# List comments to find ID
# gh issue comment 24 --list
# Then:
# gh issue comment 24 --edit <COMMENT_ID> --body-file /tmp/comment.md
```

zsh quoting tips
- Prefer heredocs with `<<'EOF'` to avoid interpolation; do not embed `\n` in quoted strings.
- Avoid complex nested quotes; use body files instead.
- Keep PR/Issue titles single-line; put details in the body file.

Quality of life
- Consider gh templates or `gh alias` wrappers that always use `--body-file`.
- Store reusable Markdown snippets under `docs/development_notes/gh_templates/` and reference them.

Cleanup
```bash
rm -f /tmp/pr-body.md /tmp/issue-body.md /tmp/comment.md
```
