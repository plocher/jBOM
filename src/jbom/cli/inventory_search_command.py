"""
Inventory search command implementation.

Searches distributor databases for parts matching existing inventory items
to validate search quality and identify improvement opportunities.
"""
import sys
import csv
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

from jbom.cli.commands import Command
from jbom.loaders.inventory import InventoryLoader
from jbom.search.mouser import MouserProvider
from jbom.search import SearchResult
from jbom.processors.search_result_scorer import SearchResultScorer
from jbom.common.types import InventoryItem


class InventorySearchCommand(Command):
    """Search for parts from external distributors based on existing inventory."""

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure inventory search command arguments."""
        parser.add_argument(
            "inventory_file", 
            help="Path to inventory file (CSV, Excel, or Numbers)"
        )

        parser.add_argument(
            "-o", "--output",
            help="Output file for enhanced inventory with search results",
        )

        parser.add_argument(
            "--report",
            help="Output file for analysis report (default: stdout)",
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
            default=3,
            help="Maximum number of candidates per inventory item (default: 3)",
        )

        parser.add_argument(
            "--api-key", 
            help="API Key for the provider (overrides env vars)"
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate input and show what would be searched without performing actual searches",
        )

        parser.add_argument(
            "--categories",
            help="Comma-separated list of categories to search (e.g., 'RES,CAP,LED'). If not specified, searches all electronic components.",
        )

    def execute(self, args: argparse.Namespace) -> int:
        """Execute inventory search command."""
        # Load inventory
        try:
            inventory_path = Path(args.inventory_file)
            if not inventory_path.exists():
                print(f"Error: Inventory file not found: {inventory_path}", file=sys.stderr)
                return 1
            
            print(f"Loading inventory from: {inventory_path}")
            loader = InventoryLoader(inventory_path)
            inventory_items, field_names = loader.load()
            
            if not inventory_items:
                print("Error: No inventory items found in file", file=sys.stderr)
                return 1
                
            print(f"Loaded {len(inventory_items)} inventory items")
            
        except Exception as e:
            print(f"Error loading inventory: {e}", file=sys.stderr)
            return 1

        # Filter items for search if categories specified
        search_items = self._filter_searchable_items(inventory_items, args.categories)
        print(f"Found {len(search_items)} searchable items")

        if args.dry_run:
            self._print_dry_run_summary(search_items)
            return 0

        # Initialize search provider
        try:
            if args.provider == "mouser":
                search_provider = MouserProvider(api_key=args.api_key)
            else:
                print(f"Error: Unknown provider '{args.provider}'", file=sys.stderr)
                return 1
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        # Perform searches
        print(f"\nSearching {search_provider.name} for {len(search_items)} items...")
        search_results = self._perform_searches(search_items, search_provider, args.limit)

        # Generate outputs
        if args.output:
            self._write_enhanced_inventory(search_results, field_names, args.output)
            print(f"Enhanced inventory written to: {args.output}")

        # Generate and output report
        report = self._generate_analysis_report(search_results, search_items)
        if args.report:
            with open(args.report, 'w') as f:
                f.write(report)
            print(f"Analysis report written to: {args.report}")
        else:
            print("\n" + "="*80)
            print("ANALYSIS REPORT")
            print("="*80)
            print(report)

        return 0

    def _filter_searchable_items(self, items: List[InventoryItem], categories: Optional[str]) -> List[InventoryItem]:
        """Filter inventory items to those suitable for distributor search."""
        searchable = []
        
        # Define categories that are typically searchable
        default_searchable_categories = {
            'RES', 'CAP', 'IND', 'LED', 'DIO', 'IC', 'Q', 'REG', 'OSC', 'FER', 'CONN'
        }
        
        if categories:
            target_categories = set(cat.strip().upper() for cat in categories.split(','))
        else:
            target_categories = default_searchable_categories
        
        for item in items:
            # Skip items without meaningful search criteria
            if not item.value or not item.category:
                continue
                
            # Skip empty or very short values
            if len(str(item.value).strip()) < 2:
                continue
                
            # Skip silkscreen, board outlines, etc.
            if item.category and item.category.upper() in ['SLK', 'BOARD', 'DOC', 'MECH']:
                continue
                
            # Include if category matches target
            if item.category and item.category.upper() in target_categories:
                searchable.append(item)
        
        return searchable

    def _print_dry_run_summary(self, items: List[InventoryItem]) -> None:
        """Print summary of what would be searched in dry run mode."""
        print(f"\nDRY RUN - Would search for {len(items)} items:")
        print("-" * 80)
        
        by_category = {}
        for item in items:
            cat = item.category.upper()
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)
        
        for category, cat_items in sorted(by_category.items()):
            print(f"\n{category} ({len(cat_items)} items):")
            for item in cat_items[:5]:  # Show first 5 in each category
                query = self._build_search_query(item)
                print(f"  {item.ipn}: '{query}'")
            if len(cat_items) > 5:
                print(f"  ... and {len(cat_items) - 5} more")

    def _perform_searches(self, items: List[InventoryItem], provider: MouserProvider, limit: int) -> List[Dict[str, Any]]:
        """Perform distributor searches for all items."""
        results = []
        scorer = SearchResultScorer()
        
        for i, item in enumerate(items, 1):
            print(f"[{i}/{len(items)}] Searching: {item.ipn} ({item.value})")
            
            query = self._build_search_query(item)
            search_result_data = {
                'inventory_item': item,
                'query': query,
                'search_results': [],
                'success': False,
                'error': None
            }
            
            try:
                # Perform search
                search_results = provider.search(query, limit=max(10, limit * 2))
                
                if search_results:
                    # Score and rank results (convert InventoryItem to Component-like object for scoring)
                    mock_component = self._inventory_to_component(item)
                    scored_results = []
                    
                    for result in search_results:
                        priority = scorer.calculate_priority(mock_component, result)
                        scored_results.append((result, priority))
                    
                    # Sort by priority and take top N
                    scored_results.sort(key=lambda x: x[1])
                    search_result_data['search_results'] = scored_results[:limit]
                    search_result_data['success'] = True
                    
                    print(f"  -> Found {len(search_results)} results, keeping top {len(scored_results[:limit])}")
                else:
                    print("  -> No results found")
            
            except Exception as e:
                search_result_data['error'] = str(e)
                print(f"  -> Error: {e}")
            
            results.append(search_result_data)
            
            # Rate limiting
            time.sleep(1.0)
        
        return results

    def _build_search_query(self, item: InventoryItem) -> str:
        """Build search query from inventory item data."""
        parts = []
        
        # Normalize value - convert Unicode symbols to ASCII
        if item.value:
            value = self._normalize_value(item.value)
            parts.append(value)
        
        # Add component type keyword
        if item.category:
            type_keywords = {
                "RES": "resistor",
                "CAP": "capacitor", 
                "IND": "inductor",
                "LED": "LED",
                "DIO": "diode",
                "IC": "IC",
                "Q": "transistor",
                "REG": "regulator",
            }
            if item.category.upper() in type_keywords:
                parts.append(type_keywords[item.category.upper()])
        
        # Add package info
        if item.package:
            parts.append(item.package)
        
        # Add tolerance if meaningful
        if item.tolerance and item.tolerance not in ['', 'N/A']:
            parts.append(item.tolerance)
        
        return " ".join(parts)

    def _normalize_value(self, value: str) -> str:
        """Normalize component values to ASCII equivalents."""
        if not value:
            return ""
        
        # Replace Unicode symbols with ASCII equivalents
        normalized = value.replace('Ω', '').replace('ω', '')
        normalized = normalized.replace('µF', 'uF').replace('μF', 'uF')
        normalized = normalized.replace('pF', 'pF').replace('nF', 'nF')
        
        # Clean up extra whitespace
        return normalized.strip()

    def _inventory_to_component(self, item: InventoryItem):
        """Convert InventoryItem to Component-like object for scoring."""
        class MockComponent:
            def __init__(self, item: InventoryItem):
                self.value = item.value or ""
                self.footprint = item.package or ""
                self.lib_id = f"{item.category or 'UNKNOWN'}:{item.ipn or 'UNKNOWN'}"
                self.properties = {
                    'Tolerance': item.tolerance or '',
                    'Voltage': item.voltage or '',
                    'Power': item.wattage or '',
                    'Type': item.type or '',
                }
        
        return MockComponent(item)

    def _write_enhanced_inventory(self, search_results: List[Dict[str, Any]], original_fields: List[str], output_path: str) -> None:
        """Write enhanced inventory with search results to CSV."""
        # Define additional fields for search results
        search_fields = [
            'Search_Query',
            'Search_Success',
            'Candidate_1_Manufacturer',
            'Candidate_1_MPN',
            'Candidate_1_Distributor_PN',
            'Candidate_1_Price',
            'Candidate_1_Availability',
            'Candidate_1_Priority_Score',
            'Candidate_2_Manufacturer',
            'Candidate_2_MPN', 
            'Candidate_2_Distributor_PN',
            'Candidate_2_Price',
            'Candidate_2_Availability',
            'Candidate_2_Priority_Score',
            'Candidate_3_Manufacturer',
            'Candidate_3_MPN',
            'Candidate_3_Distributor_PN', 
            'Candidate_3_Price',
            'Candidate_3_Availability',
            'Candidate_3_Priority_Score',
        ]
        
        all_fields = original_fields + search_fields
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=all_fields)
            writer.writeheader()
            
            # Create lookup for search results
            search_lookup = {result['inventory_item'].ipn: result for result in search_results}
            
            # Get all inventory items (including non-searched ones)
            all_items = []
            for result in search_results:
                all_items.append(result['inventory_item'])
            
            for item in all_items:
                row = item.raw_data.copy() if item.raw_data else {}
                
                # Ensure all original fields are present
                for field in original_fields:
                    if field not in row:
                        row[field] = getattr(item, field.lower(), '') or ''
                
                # Add search result data if available
                if item.ipn in search_lookup:
                    search_data = search_lookup[item.ipn]
                    row['Search_Query'] = search_data['query']
                    row['Search_Success'] = 'Yes' if search_data['success'] else 'No'
                    
                    # Add candidate data
                    for i, (result, priority) in enumerate(search_data['search_results'][:3]):
                        idx = i + 1
                        row[f'Candidate_{idx}_Manufacturer'] = result.manufacturer
                        row[f'Candidate_{idx}_MPN'] = result.mpn
                        row[f'Candidate_{idx}_Distributor_PN'] = result.distributor_part_number
                        row[f'Candidate_{idx}_Price'] = result.price
                        row[f'Candidate_{idx}_Availability'] = result.availability
                        row[f'Candidate_{idx}_Priority_Score'] = priority
                else:
                    # Item was not searched
                    for field in search_fields:
                        row[field] = ''
                
                writer.writerow(row)

    def _generate_analysis_report(self, search_results: List[Dict[str, Any]], original_items: List[InventoryItem]) -> str:
        """Generate comprehensive analysis report."""
        total_searches = len(search_results)
        successful_searches = sum(1 for r in search_results if r['success'])
        failed_searches = total_searches - successful_searches
        
        # Analyze by category
        by_category = {}
        for result in search_results:
            cat = result['inventory_item'].category.upper()
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'success': 0, 'items': []}
            by_category[cat]['total'] += 1
            if result['success']:
                by_category[cat]['success'] += 1
            by_category[cat]['items'].append(result)
        
        # Generate report
        lines = []
        lines.append(f"INVENTORY SEARCH ANALYSIS REPORT")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"")
        lines.append(f"SUMMARY")
        lines.append(f"Total items searched: {total_searches}")
        lines.append(f"Successful searches: {successful_searches} ({100*successful_searches/total_searches:.1f}%)")
        lines.append(f"Failed searches: {failed_searches} ({100*failed_searches/total_searches:.1f}%)")
        lines.append(f"")
        
        lines.append(f"RESULTS BY CATEGORY")
        lines.append(f"{'Category':<10} {'Total':<8} {'Success':<8} {'Rate':<8} {'Top Issues'}")
        lines.append(f"{'-'*60}")
        
        for cat, stats in sorted(by_category.items()):
            rate = 100 * stats['success'] / stats['total'] if stats['total'] > 0 else 0
            
            # Find common issues in failed searches
            failed_items = [item for item in stats['items'] if not item['success']]
            common_issues = self._identify_common_issues(failed_items)
            
            lines.append(f"{cat:<10} {stats['total']:<8} {stats['success']:<8} {rate:<7.1f}% {common_issues}")
        
        lines.append(f"")
        lines.append(f"INVENTORY BEST PRACTICES IDENTIFIED")
        lines.append(f"")
        
        # Identify best practices from the analysis
        best_practices = self._identify_best_practices(search_results)
        for practice in best_practices:
            lines.append(f"• {practice}")
        
        lines.append(f"")
        lines.append(f"FAILED SEARCHES DETAIL")
        lines.append(f"")
        
        failed_results = [r for r in search_results if not r['success']]
        for result in failed_results[:10]:  # Show first 10 failures
            item = result['inventory_item']
            lines.append(f"IPN: {item.ipn}")
            lines.append(f"  Value: {item.value}, Category: {item.category}, Package: {item.package}")
            lines.append(f"  Query: '{result['query']}'")
            lines.append(f"  Error: {result.get('error', 'No results found')}")
            lines.append(f"")
        
        if len(failed_results) > 10:
            lines.append(f"... and {len(failed_results) - 10} more failed searches")
        
        return "\n".join(lines)

    def _identify_common_issues(self, failed_items: List[Dict[str, Any]]) -> str:
        """Identify common patterns in failed searches."""
        if not failed_items:
            return "None"
        
        issues = []
        
        # Check for Unicode characters
        unicode_count = sum(1 for item in failed_items 
                          if any(ord(c) > 127 for c in item['query']))
        if unicode_count > len(failed_items) * 0.3:  # More than 30%
            issues.append("Unicode chars")
        
        # Check for missing package info
        no_package_count = sum(1 for item in failed_items 
                             if not item['inventory_item'].package)
        if no_package_count > len(failed_items) * 0.5:
            issues.append("Missing package")
        
        # Check for vague values
        vague_values = sum(1 for item in failed_items
                          if not item['inventory_item'].value or 
                             len(item['inventory_item'].value.strip()) < 2)
        if vague_values > len(failed_items) * 0.3:
            issues.append("Vague values")
        
        return ", ".join(issues) if issues else "Various"

    def _identify_best_practices(self, search_results: List[Dict[str, Any]]) -> List[str]:
        """Identify best practices from search analysis."""
        practices = []
        
        # Check for Unicode issues
        unicode_failures = []
        ascii_successes = []
        
        for result in search_results:
            has_unicode = any(ord(c) > 127 for c in result['query'])
            if has_unicode and not result['success']:
                unicode_failures.append(result)
            elif not has_unicode and result['success']:
                ascii_successes.append(result)
        
        if len(unicode_failures) > 2:
            practices.append("Use ASCII characters instead of Unicode symbols (Ω → ohm, µF → uF)")
        
        # Check package importance
        with_package_success = sum(1 for r in search_results 
                                 if r['inventory_item'].package and r['success'])
        without_package_success = sum(1 for r in search_results 
                                    if not r['inventory_item'].package and r['success'])
        
        total_with_package = sum(1 for r in search_results if r['inventory_item'].package)
        total_without_package = len(search_results) - total_with_package
        
        if (total_with_package > 0 and total_without_package > 0 and
            with_package_success/total_with_package > without_package_success/total_without_package + 0.2):
            practices.append("Include package/footprint information (0603, SOT-23, etc.) for better search results")
        
        # Check tolerance/specs importance  
        practices.append("Include component specifications (tolerance, voltage rating, power) when available")
        practices.append("Use standard component value formats (1k, 4.7k, 100k instead of 1000, 4700, 100000)")
        practices.append("Ensure category field uses standard abbreviations (RES, CAP, LED, IC, etc.)")
        
        return practices