---
name: git-workflow
description: jBOM project git workflow — feature branches, semantic conventional commits, and the iterative pre-commit pattern required by this repository. Use when staging changes, committing, pushing, or creating PRs in this repository.
---

# git-workflow

Procedural workflow for committing changes to the jBOM repository.
Applies to both humans onboarding and agents executing work.

## When to use

Whenever staging, committing, pushing, or creating a PR in this
repository. The iterative pre-commit pattern is **not optional** —
pre-commit hooks modify files on a first run, and a naive
`git add … && git commit` will fail when those modifications occur
after staging.

## Feature branch workflow

**Rule:** never commit directly to `main`. Always work in a feature
branch.

Branch-name conventions:

- `feature/issue-N-brief-description` — issue-based work
- `fix/issue-N-brief-description` — bug fixes
- `feature/phase-N-brief-description` — phase-based work

```bash
# Create and switch
git checkout -b feature/issue-247-docs-refresh

# Or switch to an existing branch
git checkout feature/issue-247-docs-refresh
```

## Iterative pre-commit pattern

Pre-commit hooks in this repo modify files (trailing whitespace, EOF
newlines, mixed line endings) and check for problems (yaml/json/toml
syntax, merge conflicts, debugger imports, black/flake8/bandit on
Python).

The Marines have a saying: *slow is smooth, smooth is fast.*
One-liners that try to commit and stage in one go are not smooth.

### The correct loop

```bash
# 1. Stage explicit files (preferred), or use `git add -u` to stage
#    all modifications to tracked files. Avoid `git add -A` / `git add .`
#    — those include untracked working files you don't want committed.
git add path/to/file1 path/to/file2

# 2. Run pre-commit. It will fail if it makes changes or finds problems.
pre-commit

# 3. If pre-commit modified files (auto-fixes), re-stage and re-run.
#    If pre-commit reported problems it could not auto-fix (lint, syntax,
#    etc.), fix them by hand, then re-stage and re-run.
git add -u
pre-commit

# 4. Repeat until pre-commit passes cleanly.

# 5. Commit with a conventional, semantic message.
git commit -m "type(scope): subject

Body explaining what changed and why.

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

### Anti-patterns (don't do these)

```bash
# ❌ Optimistic one-liner — fails the first time pre-commit makes a change
git add file && git commit -m "msg"

# ❌ Catch-all add — sweeps untracked working files into the commit
git add -A && git commit -m "msg"

# ❌ Bypassing pre-commit
git commit --no-verify -m "msg"
```

`--no-verify` is reserved for emergencies and requires explicit
authorization from the human supervisor before use.

## Semantic / conventional commit types

Type | Meaning | Semantic-release effect
---|---|---
`feat` | New user-facing feature | minor version bump
`fix` | Bug fix | patch version bump
`feat!` or `BREAKING CHANGE:` in footer | Breaking change | major version bump
`docs` | Documentation only | none
`test` | Add/update tests | none
`refactor` | Code change with no feature/fix | none
`perf` | Performance improvement | patch
`style` | Formatting/whitespace, no logic change | none
`chore` | Maintenance, dependencies, config | none
`ci` | CI/CD pipeline changes | none
`build` | Build system changes | none

Scope is optional and names the subsystem: `cli`, `bom`, `pos`,
`inventory`, `search`, `matcher`, `docs`, `charter`, etc.

### Commit message structure

```
type(scope): short subject in present tense, no period

Body paragraph(s) explaining what changed and why. Wrap at 72-80
columns. Reference issues with `Refs #N`, `Closes #N`, or
`Fixes #N` in the body or footer.

Co-Authored-By: Oz <oz-agent@warp.dev>
```

### Examples

```bash
git commit -m "feat(cli): add --dry-run to bom command

Adds a --dry-run flag that prints the actions jbom bom would take
without writing any output files. Useful for previewing matcher
behavior against a new inventory.

Refs #182

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

```bash
git commit -m "fix(matcher): correct tolerance gap calculation

Tolerance gaps were calculated against absolute tolerance values
instead of relative gap. Inventory items at 1% were being ranked
higher than 5% when the requirement was 10%, contradicting the
'closer to requirement wins' rule documented in ADR 0001.

Fixes #42

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

```bash
git commit -m "feat!: redesign component matching API

BREAKING CHANGE: Removes the legacy match_properties() method. Call
sites must migrate to the new score_match() interface. See ADR 0003
for the rationale.

Co-Authored-By: Oz <oz-agent@warp.dev>"
```

## Pushing and PR creation

```bash
# Push the feature branch (use -u on first push)
git push -u origin feature/issue-N-brief-description

# Create a PR via gh CLI (use --body-file for non-trivial bodies to
# avoid zsh-quoting issues with `!`, backticks, etc.)
gh pr create \
  --title "type(scope): subject" \
  --body-file /tmp/pr-body.md \
  --label documentation
```

For zsh-safe gh authoring patterns (issue bodies, comments,
multi-line content), see the `gh-issues-zsh-safe` skill once it
lands.

## Merge strategy and post-merge cleanup

Use **rebase-merge** for PRs in this repository. Rebase merges rewrite
commit SHAs, so do not rely only on ancestry checks when deciding
whether to delete branches.
Normative expectation:

- A human maintainer performs the merge in GitHub UI.
- Agents prepare the PR, validation evidence, and merge recommendation.
- Agents must not execute merge commands unless the user explicitly
  requests the agent to perform the merge.

Preferred merge options (when merge is being performed):

- GitHub UI: **Rebase and merge**
- CLI: `gh pr merge <number> --rebase` (agent only with explicit user request)

After merge, verify and clean branches with a patch-equivalence check:

```bash
# 1) Refresh refs
git fetch --prune origin

# 2) Verify branch patch is present in main
#    '-' means already applied (safe to delete), '+' means still unique
git cherry -v main feature/issue-N-brief-description

# 3) If safe (all '-' or no output), delete local branch
git branch -d feature/issue-N-brief-description

# 4) Delete remote branch if it still exists
git push origin --delete feature/issue-N-brief-description || true
```

If `git cherry` shows `+` entries, do **not** delete the branch yet.
Investigate first (wrong target branch, partial merge, or outstanding
commits not represented in `main`).

## Required co-author attribution

Every commit made by Oz must include the co-author line in the
trailer:

```
Co-Authored-By: Oz <oz-agent@warp.dev>
```

This applies to commits made through `git commit`, `gh pr create`
(if it generates a commit), and any other Oz-driven write operation.

## Troubleshooting

### Pre-commit keeps failing

Most often: pre-commit fixed something, you didn't re-stage. Run
`git diff` to see what changed, then `git add -u && pre-commit`.

### A hook reports a problem it cannot auto-fix

Hooks like `flake8`, `bandit`, and the syntax checkers report
problems they cannot mechanically fix. Fix the problem by hand
(usually a code edit), then re-stage and re-run.

### Want to see pre-commit output verbosely

```bash
# Against staged files only
pre-commit run

# Against every file in the repo
pre-commit run --all-files
```

## Related

- [`docs/README.md`](../../../docs/README.md) — documentation charter
  (lives at the docs tree root), including the
  skills-as-canonical-form clause that put this content here.
- The `WARP.md` rules at repo root govern co-author attribution and
  the broader development workflow.
