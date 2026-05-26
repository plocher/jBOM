---
name: assign-issue
description: Resolves a GitHub issue either in the current agent session or by launching a child agent, while enforcing collaborative checkpoints and the jBOM git workflow. Use when the user provides an issue number and asks to assign/resolve it with /collaborative mode and /git-workflow, optionally choosing a model for a child agent.
---

# assign-issue

## Quick start

Use this skill when the user says things like:
- "Take issue #123"
- "Assign #123 to an agent and resolve it"
- "Work issue #123 in collaborative mode with git workflow"
- "Spawn a child agent for #123 using model X"

## Inputs

Required:
- GitHub issue number (`#N`)

Optional:
- execution mode: `current-session` or `child-agent`
- child model: user-requested `model_id` (child-agent mode only; defaults to `auto (cost efficient)` when not specified)

## Workflow

### 1) Intake and activation

1. Confirm target issue number.
2. Activate collaborative behavior (`/collaborative`) for decision checkpoints.
3. Apply `git-workflow` for branch/commit/PR mechanics.

### 2) Choose execution mode

If mode is not specified, ask the user to pick:
- A) current-session
- B) child-agent

#### Mode A: current-session

Continue execution in this agent session.

#### Mode B: child-agent

1. Launch an independent child agent for implementation.
2. If user provided a model, pass it as `model_id`.
3. If no model is provided, set `model_id` to `auto` (cost efficient default).
4. Instruct child to:
   - run collaborative checkpoints on ambiguity/alternatives
   - follow `git-workflow` requirements
   - report progress, risks, and validation results

#### Recommended child-agent handoff prompt template

Use this as the default per-child handoff prompt:

Resolve GitHub issue #<N> in this repository.
Operating mode requirements:
- Use collaborative checkpoints whenever alternatives or ambiguities appear.
- Pause, present options with tradeoffs, and wait for user decision before proceeding.
- Follow the `git-workflow` skill for branch naming, iterative pre-commit loop, semantic commits, and PR creation.
Execution requirements:
- Create a feature branch named `feature/issue-<N>-<brief-slug>` (or `fix/issue-<N>-<brief-slug>` when appropriate).
- Implement the fix/feature, run required tests, and summarize validation results.
- Open a PR linked to the issue (`Closes #<N>` when appropriate).
- Post/update issue comments with progress and final resolution summary.
Reporting requirements:
- Send concise status updates at key milestones.
- Report blockers immediately with concrete options and a recommendation.

### 3) Read and frame the issue

1. Fetch issue details/comments with `gh issue view <N> --comments`.
2. Summarize:
   - problem statement
   - acceptance criteria
   - unknowns/ambiguities
3. If ambiguous, stop and run a collaborative checkpoint before coding.

### 4) Assign and announce ownership

1. Assign issue to the working assignee/identity.
2. Post a short "starting work" comment with planned approach.
3. If markdown has zsh quoting hazards, use `gh-issues-zsh-safe` patterns.

### 5) Implement with collaborative checkpoints

1. Create feature branch:
   - `feature/issue-N-brief-description` or `fix/issue-N-brief-description`
2. Work in short cycles:
   - status update
   - pause on alternatives/ambiguity
   - options + recommendation
   - wait for user decision
3. Resume only after explicit user decision.

### 6) Validate and commit via git-workflow

1. Run required tests and project gates.
2. Run iterative pre-commit loop until clean.
3. Commit with:
   - issue linkage (`Refs #N` / `Closes #N`)
   - `Co-Authored-By: Oz <oz-agent@warp.dev>`

### 7) Push, PR, and issue closure loop

1. Push feature branch.
2. Open PR linked to issue (`Closes #N` when appropriate).
3. Add substantive issue comment with:
   - change summary
   - validation run
   - PR link
4. Transition/close issue per project process.

## Guardrails

- Never commit directly to `main`.
- Do not skip collaborative checkpoints when requirements are unclear.
- If user says "normal mode" or "continue directly", exit collaborative mode and proceed.
- If user requests child mode + specific model, honor model selection.
- Do not close issue without resolution context and verification evidence.

## Done criteria

- Issue scope implemented and validated.
- PR created and linked to issue.
- Issue updated with clear resolution context.
