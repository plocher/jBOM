"""Command-line interface entry point for jBOM

Allows running jBOM as: python -m jbom [args]
"""

import sys
from .jbom import main

if __name__ == "__main__":
    sys.exit(main())
