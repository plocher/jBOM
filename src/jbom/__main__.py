"""Command-line interface entry point for jBOM (v2 CLI).

Usage:
  python -m jbom bom [options]
  python -m jbom pos [options]
"""
import sys
from .cli.main import main

if __name__ == "__main__":
    sys.exit(main())
