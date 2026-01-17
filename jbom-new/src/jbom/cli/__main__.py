"""Allow running jbom.cli as a module: python -m jbom.cli.main"""

import sys
from jbom.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
