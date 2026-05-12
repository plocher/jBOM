"""Configuration inspection command."""

from __future__ import annotations

import argparse
import json
import sys

from jbom.config.fabricators import FabricatorConfig


def register_command(subparsers) -> None:  # type: ignore[type-arg]
    """Register the ``config`` command."""

    parser = subparsers.add_parser(
        "config",
        help="Inspect configuration metadata",
        description=(
            "Inspect configuration metadata and schemas for jBOM profile models."
        ),
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Print the FabricatorConfig JSON schema",
    )
    parser.set_defaults(handler=handle_config)


def handle_config(args: argparse.Namespace) -> int:
    """Handle the ``jbom config`` command."""

    if args.schema:
        print(json.dumps(FabricatorConfig.model_json_schema(), indent=2))
        return 0

    print(
        "Error: no config action specified (try: jbom config --schema)", file=sys.stderr
    )
    return 1
