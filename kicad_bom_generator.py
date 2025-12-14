# Compatibility shim for existing tests/imports
from jbom import *  # noqa: F401,F403
# Explicitly re-export private helpers used in legacy tests
from jbom import _shorten_url, _wrap_text  # noqa: F401
