# Project skills

This directory holds project-level skills for jBOM. Each skill lives
in its own subdirectory containing a `SKILL.md` file (Warp's
tool-agnostic project-skill convention).

## Why this location

Skills live at `.agents/skills/<skill-name>/SKILL.md` because the
Warp skill loader scans specific project-relative directories
(`.agents/skills/`, `.warp/skills/`, `.claude/skills/`,
`.codex/skills/`, and similar) and does not scan `docs/`. Putting
skills in `docs/` would make them invisible to the loader.

## The `docs/skills/` symlink

`docs/skills/` is a symlink to this directory. It is a navigation
convenience so the `docs/` tree advertises the skill set without
duplicating content. The real path is here at `.agents/skills/`;
the symlink is aid only, not the source of truth.

### Windows caveat

On platforms where symlinks degrade — notably Windows without
developer mode enabled, or in repositories not configured with
`core.symlinks = true` — the `docs/skills/` path may appear as a
small text file containing the target path rather than as a navigation
hop. If you see that, navigate to `.agents/skills/` directly. The
content is the same.

The skill loader is unaffected by Windows symlink behavior; it reads
the real path here.

## Adding a new skill

1. Create a subdirectory using `kebab-case`:
   ```bash
   mkdir -p .agents/skills/my-new-skill
   ```
2. Create `SKILL.md` in that subdirectory with YAML frontmatter:
   ```markdown
   ---
   name: my-new-skill
   description: One-line description of what this skill does and when to use it.
   ---

   # my-new-skill

   ## When to use
   ...

   ## Instructions
   ...
   ```
3. Reference any supporting files (scripts, templates) from
   `SKILL.md` using paths relative to the skill subdirectory.

The `description` field is how agents decide whether to invoke the
skill — keep it specific and trigger-oriented.

## See also

- [`docs/README.md`](../../docs/README.md) — documentation charter
  (lives at the docs tree root), including the rationale for skill
  placement and the skills-as-canonical-form clause.
- Warp Skills documentation: https://docs.warp.dev/agent-platform/warp-agents/skills
