"""
InventoryEnricher for automated inventory enrichment with search results.

Combines project component extraction with distributor search to create
complete fabrication-ready inventory files.
"""
import time
from typing import List, Tuple, Optional

from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY
from jbom.search import SearchResult, SearchProvider
from jbom.processors.component_types import get_component_type
from jbom.processors.search_result_scorer import SearchResultScorer
from jbom.loaders.project_inventory import ProjectInventoryLoader


class InventoryEnricher:
    """Enriches project inventory with search results from distributors."""

    def __init__(
        self,
        components: List[Component],
        search_provider: SearchProvider,
        limit: int = 1,
        interactive: bool = False,
    ):
        """
        Initialize the inventory enricher.

        Args:
            components: List of components from KiCad project
            search_provider: Provider for part searches (e.g., Mouser)
            limit: Maximum search results per component (default: 1)
            interactive: Enable interactive candidate selection (default: False)
        """
        self.components = components
        self.search_provider = search_provider
        self.limit = limit
        self.interactive = interactive
        self.scorer = SearchResultScorer()

        # Track processing stats
        self.search_count = 0
        self.successful_searches = 0
        self.failed_searches = 0

    def enrich(self) -> Tuple[List[InventoryItem], List[str]]:
        """
        Enrich project components with search results.

        Returns:
            Tuple of (enriched inventory items, field names list)
        """
        # First generate base inventory from project components
        project_loader = ProjectInventoryLoader(self.components)
        base_items, base_fields = project_loader.load()

        # Group base items by component characteristics for search
        # We want to search unique combinations, not every component instance
        unique_components = self._group_components_for_search()

        print(
            f"Enriching inventory: {len(unique_components)} unique components to search"
        )

        enriched_items = []

        for component_group, components in unique_components.items():
            # Use the first component as representative for search
            representative = components[0]

            print(f"Searching for: {representative.reference} ({representative.value})")

            # Build search query
            query = self._build_search_query(representative)

            try:
                # Search for parts
                search_results = self.search_provider.search(
                    query, limit=max(10, self.limit * 2)
                )
                self.search_count += 1

                if search_results:
                    self.successful_searches += 1

                    # Score and rank results
                    ranked_results = self._score_and_rank_results(
                        representative, search_results
                    )

                    # Limit results based on user preference
                    if self.limit and self.limit != "none":
                        ranked_results = ranked_results[: self.limit]

                    # Create enriched inventory items
                    for i, (search_result, priority) in enumerate(ranked_results):
                        item = self._create_inventory_item(
                            representative, search_result, priority
                        )
                        enriched_items.append(item)

                        # For interactive mode, could add user prompts here

                else:
                    self.failed_searches += 1
                    # Create inventory item without search data
                    item = self._create_inventory_item(
                        representative, None, DEFAULT_PRIORITY
                    )
                    enriched_items.append(item)
                    print("  -> No search results found")

            except Exception as e:
                self.failed_searches += 1
                print(f"  -> Search error: {e}")
                # Create inventory item without search data
                item = self._create_inventory_item(
                    representative, None, DEFAULT_PRIORITY
                )
                enriched_items.append(item)

            # Rate limiting - be respectful to search providers
            time.sleep(1.0)

        # Generate comprehensive field list
        enriched_fields = self._generate_field_list(enriched_items, base_fields)

        # Print summary
        print("\nEnrichment complete:")
        print(f"  Searches performed: {self.search_count}")
        print(f"  Successful: {self.successful_searches}")
        print(f"  Failed: {self.failed_searches}")
        print(f"  Total inventory items: {len(enriched_items)}")

        return enriched_items, enriched_fields

    def _group_components_for_search(self) -> dict:
        """
        Group components by search characteristics to avoid duplicate searches.

        Returns:
            Dict mapping group key to list of components
        """
        groups = {}

        for component in self.components:
            # Skip components not in BOM
            if not component.in_bom:
                continue

            # Create grouping key based on search-relevant characteristics
            group_key = self._create_search_group_key(component)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(component)

        return groups

    def _create_search_group_key(self, component: Component) -> str:
        """Create a key for grouping similar components for search."""
        # Group by value, footprint, and key properties
        props = component.properties
        prop_key = f"{props.get('Tolerance','')}|{props.get('Voltage','')}|{props.get('Power','')}"

        return f"{component.value}|{component.footprint}|{component.lib_id}|{prop_key}"

    def _build_search_query(self, component: Component) -> str:
        """
        Build search query from component data.

        Args:
            component: KiCad component

        Returns:
            Search query string optimized for distributor search
        """
        parts = []

        # Add component value
        if component.value:
            parts.append(component.value)

        # Add component type keyword
        comp_type = get_component_type(component.lib_id, component.footprint)
        if comp_type:
            type_keywords = {
                "RES": "resistor",
                "CAP": "capacitor",
                "IND": "inductor",
                "LED": "LED",
                "DIODE": "diode",
            }
            if comp_type in type_keywords:
                parts.append(type_keywords[comp_type])

        # Add package info from footprint
        package = self._extract_package_from_footprint(component.footprint)
        if package:
            parts.append(package)

        # Add key properties
        props = component.properties
        if "Tolerance" in props and props["Tolerance"]:
            parts.append(props["Tolerance"])

        return " ".join(parts)

    def _extract_package_from_footprint(self, footprint: str) -> str:
        """Extract package designation from KiCad footprint."""
        if not footprint:
            return ""

        footprint_lower = footprint.lower()

        # Common SMD packages
        packages = [
            "0603",
            "0805",
            "1206",
            "0402",
            "1210",
            "2512",
            "sot-23",
            "sot-223",
            "soic-8",
            "soic-14",
            "soic-16",
            "qfn-16",
            "qfn-32",
            "bga-144",
        ]

        for package in packages:
            if package in footprint_lower:
                return package

        return ""

    def _score_and_rank_results(
        self, component: Component, search_results: List[SearchResult]
    ) -> List[Tuple[SearchResult, int]]:
        """
        Score and rank search results using SearchResultScorer.

        Args:
            component: KiCad component being matched
            search_results: List of search results from provider

        Returns:
            List of (SearchResult, priority) tuples, sorted by priority
        """
        scored_results = []

        for search_result in search_results:
            priority = self.scorer.calculate_priority(component, search_result)
            scored_results.append((search_result, priority))

        # Sort by priority (lower numbers = better priority)
        scored_results.sort(key=lambda x: x[1])

        return scored_results

    def _create_inventory_item(
        self,
        component: Component,
        search_result: Optional[SearchResult] = None,
        priority: int = DEFAULT_PRIORITY,
    ) -> InventoryItem:
        """
        Create inventory item from component and optional search result.

        Args:
            component: KiCad component
            search_result: Optional search result with supplier data
            priority: Priority ranking (1=best, higher=worse)

        Returns:
            Complete InventoryItem
        """
        # Start with project-based data (like ProjectInventoryLoader)
        comp_type = get_component_type(component.lib_id, component.footprint)
        category = comp_type if comp_type else "Unknown"
        package = self._extract_package_from_footprint(component.footprint)

        # Generate IPN
        if comp_type:
            ipn = f"{category}_{component.value}" if component.value else category
            ipn = ipn.replace(" ", "_")
        else:
            ipn = ""

        # Base inventory item from component
        props = component.properties

        item = InventoryItem(
            ipn=ipn,
            keywords=props.get("Keywords", ""),
            category=category,
            description=props.get(
                "Description", f"{category} {component.value} {package}"
            ),
            smd=props.get("SMD", ""),
            value=component.value,
            type=props.get("Type", ""),
            tolerance=props.get("Tolerance", ""),
            voltage=props.get("Voltage", ""),
            amperage=props.get("Amperage", ""),
            wattage=props.get(
                "Wattage", props.get("Power", "")
            ),  # Handle both Wattage and Power
            lcsc=props.get("LCSC", ""),
            manufacturer="",  # Will be filled from search result
            mfgpn="",  # Will be filled from search result
            datasheet=props.get("Datasheet", ""),
            package=package,
            distributor="",  # Will be filled from search result
            distributor_part_number="",  # Will be filled from search result
            uuid=component.uuid,
            priority=priority,
            source="Project",
            raw_data=props,
        )

        # Enhance with search result data if available
        if search_result:
            item.manufacturer = search_result.manufacturer
            item.mfgpn = search_result.mpn
            item.distributor = search_result.distributor
            item.distributor_part_number = search_result.distributor_part_number
            item.datasheet = search_result.datasheet or item.datasheet
            item.source = "Search"

            # Update description to include supplier info
            item.description = f"{search_result.description}"

            # Extract additional attributes from search result
            if "Tolerance" in search_result.attributes and not item.tolerance:
                item.tolerance = search_result.attributes["Tolerance"]
            if "Voltage" in search_result.attributes and not item.voltage:
                item.voltage = search_result.attributes["Voltage"]

        return item

    def _generate_field_list(
        self, items: List[InventoryItem], base_fields: List[str]
    ) -> List[str]:
        """
        Generate comprehensive field list for enriched inventory.

        Args:
            items: List of inventory items
            base_fields: Base field list from project

        Returns:
            Complete field list including search-enhanced fields
        """
        # Standard fields for enriched inventory
        standard_fields = [
            "IPN",
            "Category",
            "Value",
            "Package",
            "Description",
            "Keywords",
            "Manufacturer",
            "MFGPN",
            "Datasheet",
            "LCSC",
            "Tolerance",
            "Voltage",
            "Amperage",
            "Wattage",
            "Type",
            "SMD",
            "UUID",
            "Priority",
            "Distributor",
            "Distributor_Part_Number",
            "Source",
        ]

        # Add any additional fields found in raw_data
        extra_fields = set()
        for item in items:
            if item.raw_data:
                extra_fields.update(item.raw_data.keys())

        # Remove fields already in standard list
        extra_fields = [f for f in extra_fields if f not in standard_fields]

        # Combine and return
        return standard_fields + sorted(extra_fields)
