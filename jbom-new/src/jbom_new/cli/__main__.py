"""Allow running jbom_new.cli as a module: python -m jbom_new.cli.main"""

import sys
from jbom_new.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
