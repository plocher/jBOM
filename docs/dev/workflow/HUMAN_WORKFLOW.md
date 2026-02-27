# Human Workflow Guide: Paired Agent Development

## Your Role in Paired Development

You are the **architect and quality gatekeeper**. The agent is your **junior developer** who needs:
- Clear task definitions
- Active supervision
- Course correction when heading wrong direction
- Approval before moving forward

## The Basic Pattern

### Before Each Session (2 minutes)
1. Open `docs/workflow/NEXT.md` - see what task is next
2. Open `docs/workflow/planning/PHASE_1_TASKS.md` - read the full task card
3. Decide: Am I ready to work on this task?

### During Each Session (30-90 minutes)

**Step 1: Define the Task** (You)
```
Tell agent: "Let's work on Task 1.X - [task name from docs/workflow/planning/PHASE_1_TASKS.md]"
```

**Step 2: Agent Works** (Watch & Learn)
- Agent reads relevant files
- Agent creates/modifies code
- Agent explains what it's doing
- **You watch** - this is your learning time

**Step 3: Review Checkpoint** (You - CRITICAL)
Ask yourself:
- [ ] Is this following the task definition?
- [ ] Is it SIMPLE (no "improvements")?
- [ ] Do I understand what was done?
- [ ] Does it match jbom-new patterns?
- [ ] Any "grandiose monstrosity" tendencies?

**If NO to any**: Stop and course-correct immediately
```
"Wait, this looks more complex than needed. Let's simplify..."
"Why did you add X? That wasn't in the task..."
"Can you explain this design decision?"
```

**If YES to all**: Approve and move to commit

**Step 4: Validate** (You + Agent)
- Run imports: Does new code import without errors?
- Run tests: Do tests pass?
- Read code: Can you explain it to someone?

**Step 5: Commit** (Agent)
```
Ask agent: "Commit this with a semantic commit message"
```

**Step 6: Update Tracking** (You)
Update `WORK_LOG.md`:
```markdown
### Session N: Task 1.X
**Duration**: 45 minutes
**Agent**: Claude 3.5 Sonnet

**Goal**: Extract value_parsing.py from old-jbom

**What Happened**:
- Ported functions from src/jbom/common/values.py
- Added type hints and docstrings
- Fixed import for jbom-new structure

**Output**:
- Commit: abc1234
- File: jbom-new/src/jbom/common/value_parsing.py
- Tests: Not yet

**Course Corrections**:
- Asked agent to remove unnecessary validation logic (keep it simple)
- Clarified type hint for Optional[float] return

**Next**: Task 1.2b - Write tests for value_parsing
```

Update `docs/workflow/NEXT.md`:
```markdown
## Current Task
**Task 1.2b: Unit Test Value Parsing** (Ready)

## Context
value_parsing.py is complete and committed (abc1234).
Now write tests to validate the parsing functions.
...
```

### After Each Session (1 minute)
- Close gracefully: "Thanks, that's good for today"
- Mark task status in docs/workflow/planning/PHASE_1_TASKS.md
- You now know what to do next session

---

## Red Flags to Watch For

### 🚩 Agent is "Improving" Things
**What it looks like**:
- "I'll add validation here..."
- "Let me also refactor this while we're at it..."
- "I noticed we could make this more generic..."

**What to do**:
```
"Stop. The task is to port existing functionality, not improve it.
Let's stick to the original behavior from old-jbom."
```

### 🚩 Agent is Adding Complexity
**What it looks like**:
- Multiple new classes when one would do
- Abstract base classes for single implementation
- Configuration systems for simple parameters
- "Flexible architecture for future..."

**What to do**:
```
"This looks over-engineered. Show me the simplest version that works.
We can refactor later if needed."
```

### 🚩 Agent is Making Assumptions
**What it looks like**:
- "I assumed you wanted..."
- "I inferred that..."
- "It made sense to also..."

**What to do**:
```
"Don't assume. If the task doesn't specify it, ask me first.
Let's undo that assumption and stick to the requirements."
```

### 🚩 You Don't Understand the Code
**What it looks like**:
- Code is clever but unclear
- You can't explain what it does
- "Magic" happening somewhere

**What to do**:
```
"I don't understand this. Explain it step by step.
If it's too complex to explain simply, let's simplify it."
```

---

## Your Review Checklist Template

Copy this for each code review:

```
## Task 1.X Review

### Understanding
- [ ] I can explain what this code does
- [ ] I understand why it's structured this way
- [ ] No "magic" or surprising behavior

### Simplicity
- [ ] Code is as simple as possible
- [ ] No premature optimization
- [ ] No unnecessary abstractions
- [ ] Matches old-jbom behavior (not "improved")

### Architecture
- [ ] Follows jbom-new patterns (check design-patterns.md)
- [ ] Pure functions or clean services (no mixed responsibilities)
- [ ] No anti-patterns (check anti-patterns.md after Task 1.1)
- [ ] Domain layer doesn't import from CLI/application

### Testing
- [ ] Tests are readable
- [ ] Tests cover typical and edge cases
- [ ] Tests pass (I ran them)
- [ ] No over-engineering in test code

### Documentation
- [ ] Type hints are clear and accurate
- [ ] Docstrings explain purpose with examples
- [ ] Comments only where logic is non-obvious

### Commitment Check
- [ ] Ready to commit this code
- [ ] Confident it won't need immediate rewrite
- [ ] Willing to build on this in next task

If ANY checkbox is unchecked: Discuss with agent before approving
```

---

## Session Templates for Common Situations

### Starting a New Task
```
"Let's work on Task 1.X - [name]

Here's what I understand from the task card:
- We're porting [what] from [where]
- Success means [criteria]
- I want to watch for [concerns]

Show me your plan before you start coding."
```

### When Agent is Going Off Track
```
"Pause. I think we're diverging from the task.

The task says: [quote task definition]
What you're doing: [describe]
Why this concerns me: [explain]

Let's reset and try again with focus on [specific constraint]."
```

### When You Don't Understand
```
"I need you to explain this more clearly.

What I don't understand: [specific part]
What I need to know: [what would help]

Use simple language and concrete examples."
```

### When Code Looks Good
```
"This looks good. Let me verify:

1. [Check point 1] - ✅
2. [Check point 2] - ✅
3. [Check point 3] - ✅

Approved. Let's commit with message:
'feat: [what was accomplished]'
"
```

---

## Learning Opportunities

### What to Notice
As you work through tasks, pay attention to:

**Agent Strengths**:
- What tasks does agent do well?
- When is agent most helpful?
- What questions lead to good results?

**Agent Weaknesses**:
- What requires frequent correction?
- What patterns of mistakes repeat?
- When do you need to intervene?

**Your Growth**:
- Are you getting better at defining tasks?
- Are reviews getting faster?
- Are course corrections getting earlier?
- Do you understand architecture better?

### Document Your Learning
Add to `WORK_LOG.md` at end of each week:

```markdown
## Week N Retrospective

### What Worked Well
- [Thing 1]
- [Thing 2]

### What Needs Improvement
- [Thing 1]
- [Thing 2]

### Patterns I Noticed
- Agent tends to [pattern]
- I need to watch for [signal]
- Best results when I [technique]

### Questions for Next Week
- [Question 1]
- [Question 2]
```

---

## Emergency Recovery

### If Session Goes Badly Wrong
1. **Stop immediately** - don't let agent continue
2. **Check git status** - what was changed?
3. **Revert if needed**: `git checkout -- [files]`
4. **Review what went wrong** - write it down
5. **Adjust approach** - make task definition clearer
6. **Try again** - fresh session, fresh start

### If You're Unsure About Progress
1. **Pause the work** - it's okay to stop
2. **Review PHASE_1_TASKS.md** - are you on track?
3. **Check completed work** - does it still make sense?
4. **Ask for human help** - consult colleague/mentor
5. **Resume when clear** - clarity before speed

---

## Success Metrics

### Good Session
- ✅ Task completed as defined
- ✅ You understand the output
- ✅ One or fewer course corrections
- ✅ Code committed with confidence
- ✅ Clear what to do next

### Great Session
- ✅ All "Good Session" criteria
- ✅ You learned something new
- ✅ Agent followed patterns without prompting
- ✅ Tests pass first time
- ✅ Ready to continue immediately

### Warning Signs
- ⚠️ Multiple course corrections needed
- ⚠️ You're confused about the output
- ⚠️ Code more complex than expected
- ⚠️ Took much longer than estimated
- ⚠️ Not sure if task is done

If you see warning signs: **Pause and reflect** before next session

---

## Remember

**You're in charge.** The agent works for you, not the other way around.

**Slow is smooth, smooth is fast.** Taking time to review prevents rewrites.

**Clarity beats speed.** Understanding each step > rushing to completion.

**Simple beats clever.** Code you understand > code that's "elegant".

**Questions are good.** If you're unsure, ask. Agent can explain.

**It's okay to stop.** Ending session early beats going wrong direction.

---

## Next: Start Task 1.1

When you're ready to begin:
1. Read Task 1.1 in `docs/PHASE_1_TASKS.md`
2. Open Warp with Claude agent
3. Say: "Let's work on Task 1.1 - document anti-patterns from old-jbom"
4. Follow the paired workflow above

Good luck! 🚀
