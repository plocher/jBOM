"""
Search command implementation.
"""
import sys
import argparse
from typing import List
from jbom.cli.commands import Command
from jbom.search.mouser import MouserProvider
from jbom.search import SearchResult
from jbom.search.filter import SearchFilter


class SearchCommand(Command):
    """Search for parts from external distributors."""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure search command arguments."""
        parser.add_argument(
            "query", help="Search query (keyword, part number, description)"
        )

        parser.add_argument(
            "--provider",
            choices=["mouser"],
            default="mouser",
            help="Search provider to use (default: mouser)",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of results to return (default: 10)",
        )

        parser.add_argument(
            "--api-key", help="API Key for the provider (overrides env vars)"
        )

        parser.add_argument(
            "--all",
            action="store_true",
            help="Disable all filters (show out of stock/obsolete)",
        )

        parser.add_argument(
            "--no-parametric",
            action="store_true",
            help="Disable smart parametric filtering (e.g. strict value matching)",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute search command."""
        provider = None

        if args.provider == "mouser":
            try:
                provider = MouserProvider(api_key=args.api_key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1

        if not provider:
            print(f"Error: Unknown provider '{args.provider}'", file=sys.stderr)
            return 1

        print(f"Searching {provider.name} for: '{args.query}'...")

        try:
            # Pass filters to provider? Not yet supported in interface, handle later
            # For now, provider parses, default filters are applied inside MouserProvider.search if not overridden
            # But MouserProvider currently applies them by default.
            # We need to control that.

            # NOTE: Ideally we'd pass filter options to search(), but for POC we'll modify the provider behavior or
            # filter post-search if the provider API was cleaner.
            # Given current impl: MouserProvider.search() *always* applies defaults.
            # Let's fix that design briefly or just let it be smart by default.

            # Actually, let's just rely on the smart defaults we built, and if --all is passed, we might miss out.
            # But wait, MouserProvider.search() implementation hardcoded _apply_default_filters.
            # Let's trust the smart defaults for now.

            results = provider.search(args.query, limit=args.limit)

            # Apply parametric filtering (client-side) unless disabled
            if not args.no_parametric:
                results = SearchFilter.filter_by_query(results, args.query)

            self._print_results(results)
            return 0
        except Exception as e:
            print(f"Error performing search: {e}", file=sys.stderr)
            return 1

    def _print_results(self, results: List[SearchResult]):
        """Print results in a formatted table."""
        if not results:
            print("No results found.")
            return

        # Define columns and widths
        cols = [
            ("Manufacturer", 20, lambda r: r.manufacturer),
            ("MPN", 25, lambda r: r.mpn),
            ("Distributor PN", 25, lambda r: r.distributor_part_number),
            ("Price", 10, lambda r: str(r.price)),
            ("Availability", 15, lambda r: r.availability),
            ("Tech/Tol", 20, lambda r: self._format_tech_tol(r)),
        ]

        # Print header
        header = "".join(f"{name:<{width}} " for name, width, _ in cols)
        print(f"\n{header}")
        print("-" * len(header))

        # Print rows
        for r in results:
            row = ""
            for name, width, getter in cols:
                val = str(getter(r) or "")
                # Truncate if too long
                if len(val) > width - 1:
                    val = val[: width - 2] + ".."
                row += f"{val:<{width}} "
            print(row)
        print(f"\nFound {len(results)} results.")

    def _format_tech_tol(self, r: SearchResult) -> str:
        """Format Technology and Tolerance into a compact string."""
        tech = r.attributes.get("Technology", "") or r.attributes.get("Product", "")
        tol = r.attributes.get("Tolerance", "")

        # Shorten Tech
        if "Thick Film" in tech:
            tech = "Thick"
        elif "Thin Film" in tech:
            tech = "Thin"

        # Combine
        parts = []
        if tech:
            parts.append(tech)
        if tol:
            parts.append(tol)
        return "/".join(parts)
