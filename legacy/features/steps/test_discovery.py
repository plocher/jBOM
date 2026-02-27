"""
Test file to verify behave step discovery.
"""

from behave import given


@given("this is a test step for discovery")
def step_test_discovery(context):
    """Test step to verify behave can discover steps in main steps directory."""
    context.test_discovery = True


@given("a test step in the main directory")
def step_test_main_directory(context):
    """Another test step to verify main directory discovery."""
    context.main_directory_test = True
