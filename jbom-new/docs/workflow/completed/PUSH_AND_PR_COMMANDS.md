# Commands to Push Phase 1 Branch and Create PR

## After Fixing SSH Credentials

```bash
cd /Users/jplocher/Dropbox/KiCad/jBOM

# Verify git remote is correct
git remote -v
# Should show: git@github.com:plocher/jBOM.git

# Push the feature branch
git push -u origin feature/phase-1-extract-matcher

# Create PR with prepared description
cat jbom-new/docs/workflow/completed/PHASE_1_PR_DESCRIPTION.md | \
  gh pr create \
  --title "Phase 1: Extract Sophisticated Matcher from Legacy jBOM" \
  --body-file - \
  --base main \
  --label enhancement
```

## What Happens

1. **Push** uploads 30+ commits from `feature/phase-1-extract-matcher` to GitHub
2. **PR creation** automatically:
   - Creates PR against `main` branch
   - Uses full description from `PHASE_1_PR_DESCRIPTION.md`
   - Adds `enhancement` label
   - References issue #48 (will close when merged)
   - Shows 122 passing tests, deliverables, roadmap

## After PR is Created

You'll see output like:
```
https://github.com/plocher/jBOM/pull/XX
```

Then you can:
- Review in GitHub UI
- Merge directly (if no review needed)
- Or request reviews first

## To Merge After PR Approval

**Option 1: Via GitHub UI**
- Click "Merge pull request" button
- Choose merge strategy (merge commit recommended for feature branches)

**Option 2: Via CLI**
```bash
gh pr merge <PR-NUMBER> --merge
```

**Option 3: Manual merge**
```bash
git checkout main
git pull origin main
git merge feature/phase-1-extract-matcher
git push origin main
```

## After Merge

```bash
# Update local main
git checkout main
git pull origin main

# Delete feature branch (local)
git branch -d feature/phase-1-extract-matcher

# Delete feature branch (remote) - optional
git push origin --delete feature/phase-1-extract-matcher

# Verify issue #48 auto-closed
gh issue view 48
```

## Phase 1 Complete! 🎉

Next: Start Phase 2 (Fabricator selection) or celebrate the milestone!
