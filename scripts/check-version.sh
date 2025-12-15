#!/bin/bash
# Version consistency checker for jBOM
# Verifies that version numbers match across all source files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Navigate to repo root
cd "$(dirname "$0")/.."

echo "Checking version consistency across jBOM repository..."
echo ""

# Extract versions from each file
VERSION_PY=$(grep "^__version__" src/jbom/__version__.py | cut -d'"' -f2)
VERSION_TOML=$(grep "^version" pyproject.toml | head -1 | cut -d'"' -f2)
VERSION_README=$(grep "^jBOM v" README.md | head -1 | sed 's/jBOM v\([0-9.]*\).*/\1/')

# Display versions
echo "Versions found:"
echo "  __version__.py: $VERSION_PY"
echo "  pyproject.toml: $VERSION_TOML"
echo "  README.md:      $VERSION_README"
echo ""

# Check if all versions match
if [ "$VERSION_PY" = "$VERSION_TOML" ] && [ "$VERSION_PY" = "$VERSION_README" ]; then
    echo -e "${GREEN}✅ All versions match: $VERSION_PY${NC}"
    
    # Check if CLI returns same version
    CLI_VERSION=$(PYTHONPATH=src python -m jbom --version 2>&1 | grep -o "[0-9]\+\.[0-9]\+\.[0-9]\+")
    if [ "$CLI_VERSION" = "$VERSION_PY" ]; then
        echo -e "${GREEN}✅ CLI --version returns: $CLI_VERSION${NC}"
    else
        echo -e "${YELLOW}⚠️  CLI --version returns: $CLI_VERSION (expected: $VERSION_PY)${NC}"
    fi
    
    # Check git tags
    LATEST_TAG=$(git tag -l --sort=-version:refname | head -1)
    echo ""
    echo "Latest git tag: $LATEST_TAG"
    if [ "v$VERSION_PY" = "$LATEST_TAG" ]; then
        echo -e "${GREEN}✅ Version matches latest git tag${NC}"
    else
        echo -e "${YELLOW}⚠️  Version $VERSION_PY does not match latest tag $LATEST_TAG${NC}"
        echo "   This is normal if you have unreleased changes."
    fi
    
    exit 0
else
    echo -e "${RED}❌ Version mismatch detected!${NC}"
    echo ""
    echo "Please update all version locations to match."
    echo "See docs/VERSION_MANAGEMENT.md for instructions."
    exit 1
fi
