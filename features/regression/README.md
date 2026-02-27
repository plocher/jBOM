# Regression Tests

This directory contains regression tests for bugs that have been discovered and fixed.

## Purpose

- **Reproduce bugs**: Each test should demonstrate the original issue
- **Verify fixes**: Show that the bug no longer occurs
- **Prevent regressions**: Catch if the bug is reintroduced

## Naming Convention

Feature files should be named: `issue-<number>-<brief-description>.feature`

Examples:
- `issue-123-cli-crash-on-empty-plugin.feature`
- `issue-456-plugin-discovery-race-condition.feature`

If there's no issue number (bug found during development), use:
- `bug-<description>.feature`

## Template

```gherkin
@regression
Feature: [Issue #123] Brief description of the bug

  # Background: Describe the original issue
  # - What was happening?
  # - Under what conditions?
  # - What was the expected behavior?

  Scenario: Reproduce the original issue (now fixed)
    # Steps that originally caused the bug
    # This should now pass because bug is fixed

  Scenario: Edge case that could trigger regression
    # Related scenario that might break if bug returns
```

## Running Regression Tests

```bash
# Run all regression tests
behave --tags=regression

# Run specific issue
behave features/regression/issue-123-*.feature
```

## When to Add

Add a regression test when:
1. A bug is discovered (before or after fixing)
2. An edge case is found that wasn't covered by functional tests
3. A user reports an issue
4. A security vulnerability is patched
