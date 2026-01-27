# jBOM Development Workflow Quick Reference

## KiCad Validation + Efficient Behave Development

### 🚀 **TL;DR - Most Efficient Development Cycle**

```bash
# 1. Identify all issues (validation + functional)
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o failed.txt --no-capture

# 2. Work only on failures - enhanced diagnostics guide you
behave @failed.txt

# 3. Iterate until clean
behave @failed.txt  # Repeat until 0 failures

# 4. Full confidence check
unset JBOM_VALIDATE_KICAD
behave
```

## 📋 **Development Phases**

### **Normal Development** (Default - Fast)
```bash
behave features/my_feature.feature  # Fast iteration
```

### **Validation Phase** (When Developing/Validating Steps)
```bash
export JBOM_VALIDATE_KICAD=1
behave features/my_feature.feature  # Catches fake KiCad content
```

### **Focused Failure Development**
```bash
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o failed.txt      # Capture all failures
behave @failed.txt                 # Work only on failures
```

## 🔍 **When You See Enhanced Diagnostics**

KiCad validation failures show comprehensive diagnostics:

```
❌ PROJECT FILE INVENTORY:
  project.kicad_pro: 26 bytes  ← Suspiciously small!
    Preview: '(kicad_project (version 1))\n'...  ← Fake content!

✅ RESOLUTION GUIDANCE:
• Replace fake KiCad content with authentic fixtures
• Use scripts/validate_fixtures.py to check all fixtures
```

**Action**: Replace fake content with authentic KiCad fixtures

## 🛠 **Common Workflows**

### **New Feature Development**
```bash
# Create new feature, fast iteration
behave features/new_feature.feature

# Before committing, validate authenticity
export JBOM_VALIDATE_KICAD=1
behave features/new_feature.feature

# Fix any fake content found
# Commit when clean
```

### **Fixing Multiple Issues**
```bash
# Get the full picture
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o all_issues.txt

# Focus development effort
behave @all_issues.txt  # Only 5 failing instead of 192 total

# Track progress as list shrinks
behave @all_issues.txt  # Now 3 failing
behave @all_issues.txt  # Now 1 failing
behave @all_issues.txt  # All clean!
```

### **CI/CD Debugging**
```bash
# Reproduce CI failures locally
export JBOM_VALIDATE_KICAD=1
behave -f rerun -o ci_failures.txt

# Focus on CI issues
behave @ci_failures.txt
```

## ⚡ **Performance Tips**

- **Without Validation**: ~30 seconds for full suite
- **With Validation**: ~60 seconds for full suite
- **Focused on Failures**: ~5-10 seconds for typical failure count

### **Efficient Development Pattern**
```bash
# ✅ EFFICIENT: Work on failures only
behave @failed.txt  # 5-10 seconds

# ❌ INEFFICIENT: Keep running full suite
behave              # 30-60 seconds
```

## 📁 **File Management**

Files created by rerun formatter are in `.gitignore`:
- `failed_scenarios.txt`
- `*_failures.txt`
- `*_scenarios.txt`

## 🏷 **Tag-Based Development**

```bash
# Focus on specific areas
behave --tags @regression -f rerun -o regression_issues.txt
behave @regression_issues.txt

# Skip slow tests during development
behave --tags ~@slow -f rerun -o fast_failures.txt
behave @fast_failures.txt
```

## 🔧 **Integration with Existing Scenarios**

Your existing scenarios work unchanged:

```gherkin
Background:
    Given the generic fabricator is selected

Scenario: Generate basic BOM
    Given a schematic that contains:
        | Reference | Value | Footprint     |
        | R1        | 10K   | R_0805_2012   |
    When I run jbom command "bom"  # ← Validation happens here automatically
    Then the output should contain "R1"
```

**Zero scenario changes needed** - validation controlled by environment variable.

---

## 💡 **Key Insight**

This workflow gives you:
- **Fast development** when you need it (validation OFF)
- **Authentic validation** when you want it (validation ON)
- **Focused failure fixing** (rerun formatter)
- **Enhanced diagnostics** that guide you to solutions

Perfect for: *"Turn ON for step definition development/validation, turn OFF for normal iteration."*
