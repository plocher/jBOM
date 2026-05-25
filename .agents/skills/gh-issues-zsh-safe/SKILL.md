---
name: gh-issues-zsh-safe
description: zsh-safe gh CLI patterns for authoring GitHub issue bodies, PR descriptions, and comments. Use when the body content contains shell-quoting hazards — backticks, exclamation marks, dollar signs, backslashes, or multi-line Markdown — that cause literal \n or mangled text when passed inline to gh via a quoted string.
---

# gh-issues-zsh-safe

Passing multi-line Markdown to `gh` via inline shell strings is fragile in
zsh. Literal `\n` appears in the rendered body, backticks are interpreted as
command substitution, `!` triggers history expansion, and `$` expands
variables. The reliable fix is to write the body to a temporary file and
pass it with `--body-file`.

This skill covers: PR creation and editing, issue creation and editing, and
issue comment creation and editing.

## When to use

- Any time the body, description, or comment contains newlines, backticks,
  `!`, `$`, `\`, or other shell-sensitive characters.
- As a default practice — even for simple bodies, the body-file approach is
  safer and produces cleaner diffs if the body needs to be revised.

## Core rule

**Always write Markdown to a temp file; always pass `--body-file`.**
Never pass multi-line content as an inline quoted string to `gh`.

```bash
# Use mktemp for a unique, collision-free path
BODY=$(mktemp /tmp/gh-body-XXXXXX.md)
```

Prefer `mktemp` over hard-coded paths like `/tmp/pr-body.md` to avoid
collisions when multiple sessions run in parallel.

## PR bodies

### Create a PR

```bash
BODY=$(mktemp /tmp/gh-body-XXXXXX.md)
cat > "$BODY" <<'EOF'
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
  --body-file "$BODY" \
  --base main --head feature/issue-24-project-centric-implementation

rm -f "$BODY"
```

### Edit an existing PR body

```bash
BODY=$(mktemp /tmp/gh-body-XXXXXX.md)
cat > "$BODY" <<'EOF'
<updated body content here>
EOF

gh pr edit 29 --body-file "$BODY"

rm -f "$BODY"
```

## Issue bodies

### Create an issue

```bash
BODY=$(mktemp /tmp/gh-body-XXXXXX.md)
cat > "$BODY" <<'EOF'
Expand project-centric architecture coverage and regression/feature tests across all commands

Scope
- Ensure inventory subcommands (and others) follow discovery and cross-file rules like BOM/POS
- Add regression + feature tests per features/regression/README.md
- Validate base-name and directory inputs across all commands
- Verify legacy .pro discovery and hierarchical schematic handling

Acceptance Criteria
- All commands accept project directory, base name, and explicit file paths
- Regression suite updated; new behavior has feature tests
- Backward compatibility preserved

Relationship
- Related to #24; follow-up expansion.
EOF

gh issue create \
  --title "Expand project-centric architecture coverage and tests" \
  --body-file "$BODY" \
  --label enhancement

rm -f "$BODY"
```

### Edit an existing issue body

```bash
BODY=$(mktemp /tmp/gh-body-XXXXXX.md)
cat > "$BODY" <<'EOF'
<updated body content here>
EOF

gh issue edit 27 --body-file "$BODY"

rm -f "$BODY"
```

## Issue comments

### Create a comment

```bash
BODY=$(mktemp /tmp/gh-body-XXXXXX.md)
cat > "$BODY" <<'EOF'
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

gh issue comment 24 --body-file "$BODY"

rm -f "$BODY"
```

### Edit a prior comment

Finding the comment ID requires listing comments first. The `gh` CLI does
not yet have a stable `--edit` flag on `gh issue comment`; use the REST API
or the GitHub web UI for edits to existing comments. Check `gh issue comment
--help` for any `--edit` flag that may have landed in your installed version.

```bash
# List comments to find the comment ID (note: output may be long)
gh issue view 24 --comments

# If your gh version supports --edit:
# gh issue comment 24 --edit <COMMENT_ID> --body-file "$BODY"
```

## zsh quoting rules of thumb

- Use `<<'EOF'` heredocs (single-quoted delimiter) to suppress all shell
  interpolation inside the body. This makes `!`, `$var`, and backticks safe.
- Keep PR and issue **titles** single-line and free of special characters;
  pass the title directly as `--title "..."`. Put all complex content in the
  body file.
- Avoid embedding `\n` escape sequences in `--body` inline strings — they
  render literally in GitHub Markdown. Use a heredoc or actual newlines in
  the file instead.
- Never nest complex quoting; if you need the body to reference a shell
  variable, expand it before the heredoc or write the variable's value to
  the file explicitly.

## Cleanup

Remove temporary files after the `gh` call completes:

```bash
rm -f "$BODY"
```

If you use `mktemp` consistently, a single cleanup pattern suffices; there
is no risk of removing a file another session is using.

## Quality of life

Consider a shell alias or `gh alias` that always writes a temp file:

```bash
# In ~/.zshrc or a project-local alias
alias gh-pr-create='gh pr create --body-file'
```

Reusable Markdown snippets (boilerplate acceptance criteria, relationship
sections) can be kept under `docs/` or a personal snippets directory and
`cat`-ed into the heredoc before the `gh` call.

## Related

- [`git-workflow`](../git-workflow/SKILL.md) — commit, push, and PR creation
  procedure; references this skill for body-authoring patterns
- GitHub CLI docs: <https://cli.github.com/manual/gh_pr_create>
