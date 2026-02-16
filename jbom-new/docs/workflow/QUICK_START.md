# Quick Start: Paired Agent Workflow

## Before Each Work Session

```bash
# 1. Check what's next
cat jbom-new/docs/workflow/NEXT.md

# 2. Read the full task card
cat jbom-new/docs/PHASE_1_TASKS.md | less
# (search for the task in NEXT.md)

# 3. Open Warp, start working
```

## The Paired Pattern (Copy-Paste to Agent)

```
Let's work on Task 1.X - [task name]

Here's what I understand:
- We're [what we're doing]
- Success means [criteria from task card]
- I want to watch for [any concerns]

Show me your plan before you start.
```

## Your Review Questions (Ask Yourself)

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

Then **you update**:
1. `jbom-new/docs/WORK_LOG.md` - add session entry
2. `jbom-new/docs/workflow/NEXT.md` - point to next task
3. `jbom-new/docs/PHASE_1_TASKS.md` - mark task done

## Files You Need

📄 **docs/workflow/NEXT.md** - What to do right now
📄 **docs/PHASE_1_TASKS.md** - All tasks with checklists
📄 **docs/HUMAN_WORKFLOW.md** - Detailed workflow guide
📄 **docs/WORK_LOG.md** - Session history

## Key Reminders

**You're in charge** - Agent is your junior developer
**Slow is smooth** - Review prevents rewrites
**Simple beats clever** - Understand > elegant
**Stop when stuck** - Clarity before speed

---

## First Task: Task 1.1

Ready to start? Open Warp and say:

```
Let's work on Task 1.1 - document anti-patterns from old-jbom

Here's what I understand:
- We're analyzing old-jbom code to identify architectural problems
- Success means creating anti-patterns.md with 3-5 concrete examples
- I want to watch for: actual code examples, clear explanations

Show me your plan before you start.
```

Then follow the paired pattern above. Good luck! 🚀
