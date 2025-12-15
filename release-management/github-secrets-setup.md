# GitHub Secrets and Variables Configuration for jBOM

This guide explains how to configure GitHub Secrets, Variables, and Environments for automated releases and CI/CD workflows.

## Quick Summary of GitHub Security Features

| Feature | Type | Scope | Use Case |
|---------|------|-------|----------|
| **Secrets** | Encrypted | Repository or Organization | Sensitive values (API keys, tokens, passwords) |
| **Variables** | Plain text | Repository or Organization | Non-sensitive configuration values |
| **Repository Secrets** | Encrypted | Single repository | Repo-specific sensitive data |
| **Organization Secrets** | Encrypted | Multiple repositories | Shared sensitive data across org |
| **Environments** | Configuration | Repository | Environment-specific (staging, production) |
| **Environment Secrets** | Encrypted | Specific environment | Prod/staging specific sensitive data |

## For jBOM: Required Configuration

jBOM needs **1 Repository Secret** for automated PyPI publishing.

### What You Need

- **PYPI_API_TOKEN** - Your PyPI API token (required for publishing)
- **GITHUB_TOKEN** - Automatically provided by GitHub Actions (no setup needed)

## Step-by-Step Configuration

### Part 1: Get Your PyPI API Token

1. Go to https://pypi.org/account/
2. Log in to your PyPI account
3. Click **Account settings** (top right)
4. In the left sidebar, click **API tokens**
5. Click **Add API token**
6. Name it: `github-jbom-releases`
7. Select scope: **Entire account** (or create per-project token)
8. Click **Create token**
9. **Copy the token** (starts with `pypi-`)
   - ⚠️ This is the only time you'll see it - copy it now
   - Format: `pypi-XXXXXXXXXXXXXXXXXXXXXXXXXX` (long string of characters)
   - NEVER share or commit this token

### Part 2: Add Repository Secret to GitHub

#### Via GitHub Web UI (Easiest)

1. Go to your repository: https://github.com/plocher/jBOM
2. Click **Settings** (top right)
3. In left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** (green button, top right)
5. Configure:
   - **Name**: `PYPI_API_TOKEN`
   - **Secret**: Paste your PyPI token (the value starting with `pypi-`)
6. Click **Add secret**

✅ Done! The secret is now available to workflows.

#### Via GitHub CLI (Alternative)

```bash
# If you have GitHub CLI installed
gh secret set PYPI_API_TOKEN \
  --repo plocher/jBOM \
  --body "YOUR_ACTUAL_TOKEN_HERE"
# Replace YOUR_ACTUAL_TOKEN_HERE with your actual PyPI token
```

Or interactively:
```bash
gh secret set PYPI_API_TOKEN --repo plocher/jBOM
# Paste your token when prompted (won't echo to screen)
```

### Part 3: Verify Secret Configuration

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. You should see:
   - **Repository secrets**
     - `PYPI_API_TOKEN` (with last 4 characters visible: `...Xq3k`)
   - **Repository variables** (none needed for jBOM)

3. Verify in your workflows are using it correctly:
   - Look for `${{ secrets.PYPI_API_TOKEN }}` in `.github/workflows/publish.yml`

## Understanding Secret Types in jBOM Workflows

### Repository Secrets (What jBOM Uses)

**Definition**: Encrypted secrets stored at repository level, available to all workflows in that repo.

**For jBOM**:
```yaml
# In .github/workflows/publish.yml
with:
  password: ${{ secrets.PYPI_API_TOKEN }}  # ← Repository secret
```

**Access**:
- Available to all workflows in the repository
- Not visible to workflows from forked repos (security feature)
- Visible to: Repo admins only (encrypted in UI)

**When to use**: Single repository, direct publishing

### Organization Secrets (If You Have Multiple Projects)

**Definition**: Encrypted secrets shared across multiple repositories in an organization.

**When to use**:
- Multiple Python projects need PyPI access
- Same token used across organization
- Centralized management

**Setup** (requires org admin):
1. Go to Organization settings
2. Click **Secrets and variables** → **Actions**
3. Click **New organization secret**
4. Configure:
   - **Name**: `PYPI_API_TOKEN`
   - **Secret**: Your PyPI token
   - **Repository access**: Select which repos can use it (or "All")

**In workflow** (same syntax as repo secret):
```yaml
password: ${{ secrets.PYPI_API_TOKEN }}
```

## Understanding Variables (Non-Sensitive Configuration)

### Repository Variables

**Definition**: Plain text, non-encrypted configuration values at repository level.

**For jBOM - Optional Use Cases**:
- Package version for display
- Project metadata
- Non-secret URLs

**Example Setup** (if needed):
```
Name: PACKAGE_NAME
Value: jbom
```

**In workflow**:
```yaml
echo "Publishing ${{ vars.PACKAGE_NAME }}"
```

### Organization Variables

**Definition**: Plain text variables shared across organization repositories.

**Usage**: Same as repository variables, just at org level.

**When to use**: Shared configuration across multiple projects.

## Understanding Environments (For Advanced Setup)

### What Are Environments?

**Definition**: Deployment targets with their own protection rules and secrets.

**Common Use Cases**:
- `production` - Live PyPI
- `staging` - Test PyPI
- `development` - Local testing

### For jBOM - Optional Advanced Setup

If you want **separate tokens for TestPyPI and PyPI**:

**Step 1: Create Environments**

1. Go to **Settings** → **Environments**
2. Click **New environment**
3. Create two:
   - `production` (for PyPI)
   - `staging` (for TestPyPI)

**Step 2: Add Environment-Specific Secrets**

For `production` environment:
1. Click on `production` environment
2. Under **Secrets**, click **Add secret**
3. Name: `PYPI_API_TOKEN`
4. Value: Your PyPI token

For `staging` environment:
1. Click on `staging` environment
2. Under **Secrets**, click **Add secret**
3. Name: `PYPI_API_TOKEN`
4. Value: Your TestPyPI token

**Step 3: Use in Workflows**

```yaml
# In .github/workflows/publish.yml
jobs:
  publish-to-production:
    environment: production  # ← Use production environment
    runs-on: ubuntu-latest
    steps:
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

**Benefits**:
- Different tokens for different environments
- Can require approvals before deploying to production
- Clearer separation of concerns

## Current jBOM Setup Recommendation

For jBOM, use the **simple approach**:

### What to Configure

1. ✅ **Repository Secret** (required):
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI API token
   - Scope: Repository level

2. ✅ **GITHUB_TOKEN** (automatic):
   - Provided by GitHub Actions automatically
   - No configuration needed
   - Used for: Creating releases, pushing commits

3. ❌ **Organization Secrets** (not needed):
   - Unless you have multiple Python projects

4. ❌ **Variables** (not needed):
   - jBOM doesn't use configuration variables

5. ❌ **Environments** (not needed unless):
   - You want separate TestPyPI and PyPI tokens
   - You want approval workflows before production releases

## Troubleshooting

### Secret Not Working in Workflow

**Problem**: Workflow fails with "Invalid token" or "Unauthorized"

**Solutions**:
1. Verify secret name matches exactly: `PYPI_API_TOKEN`
2. Check syntax: `${{ secrets.PYPI_API_TOKEN }}`
3. Confirm token isn't expired on PyPI
4. Verify token has upload permission
5. Ensure secret is at correct scope (Repository vs Organization)

### Secret Visible in Logs

**Problem**: Token appears in GitHub Actions logs

**Solution**:
- GitHub automatically masks known secrets in logs
- If visible, regenerate token immediately on PyPI
- Use `::add-mask::` in workflow if needed (advanced)

### Fork Not Getting Secrets

**Problem**: Forked PR doesn't have access to secrets

**Expected behavior** (for security):
- Secrets not available in workflows triggered by forks
- Protects against accidental token leaks in malicious PRs
- Public workflows can still run

### Organization Secret Conflict

**Problem**: Both repo and org secret with same name

**Resolution**:
- Repo secret takes precedence
- Use one or the other, not both

## Security Best Practices

1. ✅ **Use Repository Secrets for sensitive values**
   - API tokens
   - Passwords
   - Private keys

2. ✅ **Rotate tokens periodically**
   - PyPI allows creating multiple tokens
   - Delete old ones after rotation

3. ✅ **Use minimal permissions**
   - PyPI tokens can be scoped to specific projects
   - Only allow "upload" permission

4. ✅ **Don't commit secrets**
   - Never put tokens in `.py`, `.toml`, or config files
   - Use secrets always

5. ✅ **Review workflow permissions**
   - Check who can trigger releases
   - Require approvals for sensitive actions

6. ❌ **Don't log secrets**
   - GitHub masks them, but never echo them manually
   - Don't pass to commands that log output

## Verification Checklist

After setup, verify everything works:

- [ ] Repository Secret `PYPI_API_TOKEN` created
- [ ] Workflows can access `${{ secrets.PYPI_API_TOKEN }}`
- [ ] Push test commit with `fix:` prefix
- [ ] Verify test.yml workflow runs and passes
- [ ] Verify semantic-release.yml creates version bump
- [ ] Verify git tag is created (check GitHub releases)
- [ ] Verify publish.yml triggered on release
- [ ] Verify package published to PyPI
- [ ] Check https://pypi.org/project/jbom/ for new version

## Reference: GitHub Actions Secret Variables

Common patterns in jBOM workflows:

```yaml
# Repository Secret
${{ secrets.PYPI_API_TOKEN }}

# Automatic GitHub Token (no setup needed)
${{ secrets.GITHUB_TOKEN }}

# Repository Variable (if used)
${{ vars.PACKAGE_NAME }}

# Environment Secret
${{ secrets.PRODUCTION_TOKEN }}

# Combined in workflow_dispatch input
${{ github.event.inputs.token }}
```

## More Information

- GitHub Docs: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- PyPI API Tokens: https://pypi.org/help/#apitoken
- GitHub Environments: https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment
