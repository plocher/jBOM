# Makefile for jBOM developer tasks

# Tools
PY ?= python3
PIP ?= pip3

# Env
export PYTHONPATH := src

# Real inventory and project roots (override as needed)
INVENTORY ?= /Users/jplocher/Dropbox/KiCad/spcoast-inventory/SPCoast-INVENTORY.numbers
PROJECTS  ?= /Users/jplocher/Dropbox/KiCad/projects
# Comma-separated list of specific projects to test
PROJECTS_LIST ?= /Users/jplocher/Dropbox/KiCad/projects/Core-wt32-eth0,/Users/jplocher/Dropbox/KiCad/projects/AltmillSwitches,/Users/jplocher/Dropbox/KiCad/projects/Brakeman-RED

# Test module lists
UNIT_MODULES := $(shell ls tests/test_*.py | grep -v 'test_inventory_numbers_real.py' | grep -v 'test_integration_projects.py' | sed -e 's|/|.|g' -e 's|\\.py$$||')
INTEGRATION_MODULES := tests.test_inventory_numbers_real tests.test_integration_projects

.PHONY: help test unit integration clean

help:
	@echo "jBOM Makefile targets:"
	@echo "  make test          - run all tests (unit + integration)"
	@echo "  make unit          - run unit tests only"
	@echo "  make integration   - run integration tests (Numbers inventory + real projects)"
	@echo "  make clean         - remove temporary artifacts"
	@echo ""
	@echo "Variables (override with make VAR=value):"
	@echo "  PY=<python>        - Python executable (default: $(PY))"
	@echo "  INVENTORY=<path>   - Inventory file for integration tests (default: $(INVENTORY))"
	@echo "  PROJECTS=<dir>     - KiCad projects root for integration tests (default: $(PROJECTS))"
	@echo "  PROJECTS_LIST=csv   - Specific projects to target (default: $(PROJECTS_LIST))"

# Aggregate
test: unit integration

# Unit tests (exclude integration modules)
unit:
	@echo "[unit] Running: $(UNIT_MODULES)"
	$(PY) -m unittest -v $(UNIT_MODULES)

# Integration tests (real inventory and projects)
integration:
	@echo "[integration] Running: $(INTEGRATION_MODULES)"
INVENTORY=$(INVENTORY) PROJECTS=$(PROJECTS) PROJECTS_LIST=$(PROJECTS_LIST) $(PY) -m unittest -v $(INTEGRATION_MODULES)

clean:
	rm -rf __pycache__ */__pycache__ .pytest_cache tmp_* tmp_project_pos *.egg-info build dist
