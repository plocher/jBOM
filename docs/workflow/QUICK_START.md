# Quick Start: Paired Agent Workflow

## Before Each Work Session

```bash
# 1. Check what's next
cat jbom-new/docs/workflow/NEXT.md

# 2. Read the full task card
cat jbom-new/docs/workflow/planning/PHASE_x_TASKS.md
# (You should find the task mentioned in NEXT.md)

# 3. Open Warp, start working with the sub-agent
```

## The Paired Pattern (Copy-Paste to Sub-Agent)

Ready to start? Open Warp and say:

```
/agent You are a python software developer and a systems architect helping me to address tech debt in an existing code base.  We are refactoring an electronic design tool called jBOM into a modular and better defined jbom-new.

We are in the jBOM git repo: `~/Dropbox/KiCad/jBOM` with a remote github origin, and should be doing our work in a feature branch.
We are in the directory `jbom-new/docs/workflow`
The big picture is in `./planning/PHASE_2_TASKS.md`.

We will focus on the task found in the colaboration document `./NEXT.md`

Use the markdown documents in `./planning/ [README.md, QUICK_START.md, GIT_WORKFLOW.md]` and `../architecture/*` to guide your work
Update `./WORK_LOG.md` to reflect what has been completed.

You are authorized to perform git commits with a reasonable conventional message in this branch, after pre-commit and the specified tests pass. If that is a problem, you can always ask me to do the commit

Show me your plan before you start.
```

## Review Questions (Ask Yourself)

✅ **Is it SIMPLE?** No "improvements", no extra features
✅ **Do I UNDERSTAND it?** Can I explain it to someone?
✅ **Does it MATCH the task?** Doing what was asked, not more
✅ **Is it CLEAN?** Follows jbom-new patterns (check design-patterns.md)

**If ANY is NO**: Course-correct immediately, don't wait

## When to Stop Agent

🚩 "I'll also add..." → **STOP**: Just do the task
🚩 "I assumed..." → **STOP**: Ask first, don't assume
🚩 "More flexible..." → **STOP**: Simple over clever
🚩 You're confused → **STOP**: Get clarity first

## Ending the Session

```
This looks good. Let's commit with message:
'feat: [what we accomplished]'

Include co-author line:
Co-Authored-By: Warp <agent@warp.dev>
```

Then **ysub-agent updates**:
1. `jbom-new/docs/WORK_LOG.md` - add session entry
2. `jbom-new/docs/workflow/NEXT.md` - point to next task
3. `jbom-new/docs/PHASE_1_TASKS.md` - mark task done

## Files You Need

📄 **docs/workflow/NEXT.md** - What to do right now
📄 **docs/PHASE_2_TASKS.md** - All tasks with checklists
📄 **docs/HUMAN_WORKFLOW.md** - Detailed workflow guide
📄 **docs/WORK_LOG.md** - Session history

## Key Reminders

**You're in charge** - Agent is your junior developer
**Slow is smooth** - Review prevents rewrites
**Simple beats clever** - Understand > elegant
**Stop when stuck** - Clarity before speed
