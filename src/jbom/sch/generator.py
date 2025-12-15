"""BOM generation from components and inventory matches.

Generates bill of materials (BOM) from parsed KiCad components,
matching them against inventory items to produce fabrication-ready output.
"""

import re
from typing import List, Dict, Optional, Tuple

from jbom.common.types import Component, InventoryItem, BOMEntry
from jbom.common.constants import (
    ComponentType,
    DiagnosticIssue,
    CommonFields,
    SMDType,
    PRECISION_THRESHOLD,
)
from jbom.common.packages import PackageType
from jbom.sch.types import get_component_type
from jbom.inventory.matcher import InventoryMatcher


class BOMGenerator:
    """Generates bill of materials from components and inventory matches"""

    def __init__(self, components: List[Component], matcher: InventoryMatcher):
        self.components = components
        self.matcher = matcher

    def generate_bom(
        self, verbose: bool = False, debug: bool = False, smd_only: bool = False
    ) -> Tuple[List[BOMEntry], int, List[dict]]:
        """Generate bill of materials"""
        bom_entries: List[BOMEntry] = []
        debug_diagnostics: List[dict] = []

        # Group components by value and footprint
        grouped_components = self._group_components()

        for group_key, group_components in grouped_components.items():
            reference = group_components[0].reference
            quantity = len(group_components)

            # Find matches for first component in group
            matches = self.matcher.find_matches(group_components[0], debug=debug)

            if matches:
                # Use best match
                if debug:
                    best_item, score, match_debug = matches[0]
                else:
                    best_item, score, _ = matches[0]

                # Determine if schematic implies 1% (explicit trailing zero like 10k0 or Tolerance <=1%)
                comp0 = group_components[0]
                desired_1pct = False
                # explicit precision pattern (any trailing digit after unit indicates precision)
                if (
                    get_component_type(comp0.lib_id, comp0.footprint)
                    == ComponentType.RESISTOR
                ):
                    explicit_precision = bool(
                        re.match(r"^\s*\d+[kKmMrR]\d+\s*", comp0.value or "")
                    )
                    tol_str = (
                        (comp0.properties.get(CommonFields.TOLERANCE) or "")
                        .strip()
                        .replace("%", "")
                    )
                    tol_ok = False
                    try:
                        tol_ok = (
                            float(tol_str) <= PRECISION_THRESHOLD if tol_str else False
                        )
                    except ValueError:
                        tol_ok = False
                    desired_1pct = explicit_precision or tol_ok

                # Check inventory for any 1% option among candidates
                has_1pct_option = any(
                    ((itm.tolerance or "").strip().startswith("1%"))
                    for itm, _, _ in matches
                )
                warn = ""
                if desired_1pct and not has_1pct_option:
                    best_tol = (best_item.tolerance or "").strip() or "unknown"
                    warn = f" Warning: schematic implies 1% resistor but no 1% inventory item found (best tolerance {best_tol})."

                # Create BOM entry with tie handling
                display_value = self._format_display_value(comp0)
                base_notes, viable_alts = self._analyze_matches(
                    matches, best_item, verbose
                )

                # Debug information is handled by verbose console output, not BOM notes
                notes_combined = (base_notes + warn).strip()
                entry = BOMEntry(
                    reference=", ".join([c.reference for c in group_components]),
                    quantity=quantity,
                    value=display_value,
                    footprint=comp0.footprint,
                    lcsc=best_item.lcsc,
                    manufacturer=best_item.manufacturer,
                    mfgpn=best_item.mfgpn,
                    description=best_item.description,
                    datasheet=best_item.datasheet,
                    smd=best_item.smd,
                    match_quality=f"Score: {score}",
                    notes=notes_combined,
                    priority=best_item.priority,
                )

                bom_entries.append(entry)

                # Add viable alternative matches only
                for additional_item, additional_score in viable_alts:
                    additional_entry = BOMEntry(
                        reference=f"ALT: {', '.join([c.reference for c in group_components])}",
                        quantity=quantity,
                        value=display_value,
                        footprint=group_components[0].footprint,
                        lcsc=additional_item.lcsc,
                        manufacturer=additional_item.manufacturer,
                        mfgpn=additional_item.mfgpn,
                        description=additional_item.description,
                        datasheet=additional_item.datasheet,
                        smd=additional_item.smd,
                        match_quality=f"Score: {additional_score}",
                        notes="Alternative match",
                        priority=additional_item.priority,
                    )
                    bom_entries.append(additional_entry)
            else:
                # No matches found - provide diagnostic information in debug mode
                comp0 = group_components[0]
                display_value = self._format_display_value(comp0)

                debug_notes = ""
                diagnostic_data = None
                if debug:
                    diagnostic_data = self._analyze_no_match_component(comp0)
                    debug_notes = self._format_diagnostic_for_bom(diagnostic_data)

                notes = "No inventory match found" + (
                    debug_notes if debug_notes else ""
                )

                entry = BOMEntry(
                    reference=", ".join([c.reference for c in group_components]),
                    quantity=quantity,
                    value=display_value,
                    footprint=comp0.footprint,
                    lcsc="",
                    manufacturer="",
                    mfgpn="",
                    description="",
                    datasheet="",
                    smd="",
                    match_quality="No match",
                    notes=notes,
                )
                bom_entries.append(entry)

                # Only collect diagnostic for console output if component will be included in final BOM
                if debug and diagnostic_data:
                    # Create a temporary entry to check SMD status for filtering
                    temp_entry = entry
                    if not smd_only or self._is_smd_component(temp_entry):
                        debug_diagnostics.append(diagnostic_data)

        # Filter for SMD components only if requested
        excluded_count = 0
        if smd_only:
            original_count = len(bom_entries)
            # Filter BOM entries
            filtered_entries = []
            for entry in bom_entries:
                if self._is_smd_component(entry):
                    filtered_entries.append(entry)
            bom_entries = filtered_entries
            excluded_count = original_count - len(bom_entries)

        # Sort BOM entries by category and component numbering
        bom_entries.sort(key=self._bom_sort_key)
        return bom_entries, excluded_count, debug_diagnostics

    def _is_smd_component(self, entry: BOMEntry) -> bool:
        """Check if a BOM entry represents an SMD component based on inventory data"""
        # Check the SMD field from the matched inventory item
        smd_field = (entry.smd or "").strip().upper()

        # Explicit SMD marking
        if smd_field in SMDType.SMD_VALUES:
            return True

        # Explicit non-SMD marking
        elif smd_field in SMDType.PTH_VALUES:
            return False

        # For unclear/empty SMD field, try to infer from footprint
        elif not smd_field or smd_field in SMDType.UNKNOWN_VALUES:
            footprint = (entry.footprint or "").lower()

            # Check for SMD package indicators in footprints
            if any(indicator in footprint for indicator in PackageType.SMD_PACKAGES):
                return True
            # Check for through-hole indicators
            elif any(
                indicator in footprint
                for indicator in PackageType.THROUGH_HOLE_PACKAGES
            ):
                return False

            # For SMD filtering: if uncertain, exclude (strict SMD-only)
            return False

        else:
            # Unknown/unexpected SMD field values (like "Q16", "R12" etc.)
            # These are likely data errors or non-SMD related fields
            import sys

            print(
                f"Warning: Unexpected SMD field value '{smd_field}' for component {entry.reference} - treating as non-SMD",
                file=sys.stderr,
            )
            return False

    def _analyze_no_match_component(self, component: Component) -> dict:
        """Analyze a component with no inventory matches and return structured diagnostic data"""
        # Component analysis
        comp_type = get_component_type(component.lib_id, component.footprint)
        comp_pkg = self.matcher._extract_package_from_footprint(component.footprint)
        comp_val_norm = (
            self.matcher._normalize_value(component.value) if component.value else ""
        )

        # Check for candidates by value and type without package filtering
        value_matches = 0
        type_matches = 0
        package_mismatches = []

        for item in self.matcher.inventory:
            # Check type matching
            if comp_type and comp_type in (item.category or "").upper():
                type_matches += 1

                # Check value matching for same type
                if comp_val_norm and self.matcher._values_match(
                    component.value, item.value
                ):
                    value_matches += 1

                    # Check if package is the issue
                    if comp_pkg:
                        item_pkg = (item.package or "").lower()
                        if comp_pkg not in item_pkg:
                            package_mismatches.append((item, comp_pkg, item.package))

        # Determine issue type and details
        if comp_type:
            if type_matches == 0:
                issue_type = DiagnosticIssue.NO_TYPE_MATCH
                issue_details = {"comp_type": comp_type}
            elif value_matches == 0 and component.value:
                issue_type = DiagnosticIssue.NO_VALUE_MATCH
                issue_details = {"comp_type": comp_type, "value": component.value}
            elif package_mismatches and comp_pkg:
                available_packages = set(
                    item.package for item, _, _ in package_mismatches if item.package
                )
                if available_packages:
                    issue_type = DiagnosticIssue.PACKAGE_MISMATCH
                    issue_details = {
                        "value": component.value,
                        "available_packages": sorted(available_packages),
                        "required_package": comp_pkg,
                    }
                else:
                    issue_type = DiagnosticIssue.PACKAGE_MISMATCH_GENERIC
                    issue_details = {"required_package": comp_pkg}
            else:
                issue_type = DiagnosticIssue.NO_MATCH
                issue_details = {}
        else:
            issue_type = DiagnosticIssue.TYPE_UNKNOWN
            issue_details = {}

        return {
            "component": {
                "reference": component.reference,
                "lib_id": component.lib_id,
                "value": component.value,
                "footprint": component.footprint,
            },
            "analysis": {
                "type": comp_type,
                "package": comp_pkg,
                "value_normalized": comp_val_norm,
            },
            "issue": {"type": issue_type, "details": issue_details},
        }

    def _generate_diagnostic_message(
        self, diagnostic_data: dict, format_type: str
    ) -> str:
        """Generate diagnostic message from structured data for different output formats.

        Both formats contain the same diagnostic information, just formatted differently:
        - BOM format: semicolon-separated with DEBUG prefix for CSV compatibility
        - Console format: user-friendly multi-line format for readability

        Args:
            diagnostic_data: Structured diagnostic data
            format_type: 'bom' for BOM file format, 'console' for user-friendly console format
        """
        comp = diagnostic_data["component"]
        analysis = diagnostic_data["analysis"]
        issue = diagnostic_data["issue"]

        if format_type == "bom":
            # BOM format: concise semicolon-separated format for CSV compatibility
            lib_namespace = ""
            if ":" in comp["lib_id"]:
                lib_namespace, _ = comp["lib_id"].split(":", 1)

            # Use concise component description like console format
            if not analysis["type"]:
                lib_part = (
                    comp["lib_id"].split(":", 1)[1]
                    if ":" in comp["lib_id"]
                    else comp["lib_id"]
                )
                comp_desc = f"Component: {comp['reference']} ({comp['lib_id']}) from {lib_namespace} (part: {lib_part})"
            else:
                type_names = {
                    ComponentType.RESISTOR: "Resistor",
                    ComponentType.CAPACITOR: "Capacitor",
                    ComponentType.INDUCTOR: "Inductor",
                    ComponentType.DIODE: "Diode",
                    ComponentType.LED: "LED",
                    ComponentType.INTEGRATED_CIRCUIT: "IC",
                    ComponentType.CONNECTOR: "Connector",
                    ComponentType.SWITCH: "Switch",
                    ComponentType.TRANSISTOR: "Transistor",
                }
                type_name = type_names.get(analysis["type"], analysis["type"])
                package_text = f" {analysis['package']}" if analysis["package"] else ""
                value_text = f" {comp['value']}" if comp["value"] else ""
                comp_desc = f"Component: {comp['reference']} ({comp['lib_id']}) is a{value_text}{package_text} {type_name}"

            # Generate issue message
            issue_msg = self._format_issue_message(issue, analysis.get("type"))

            return f" {comp_desc}; Issue: {issue_msg}"

        elif format_type == "console":
            # Console format: concise user-friendly format with same core information
            lib_namespace = ""
            if ":" in comp["lib_id"]:
                lib_namespace, _ = comp["lib_id"].split(":", 1)

            # Format main component description (contains same info as BOM format)
            if not analysis["type"]:
                lib_part = (
                    comp["lib_id"].split(":", 1)[1]
                    if ":" in comp["lib_id"]
                    else comp["lib_id"]
                )
                main_desc = f"Component {comp['reference']} from {lib_namespace} (part: {lib_part})"
            else:
                type_names = {
                    ComponentType.RESISTOR: "Resistor",
                    ComponentType.CAPACITOR: "Capacitor",
                    ComponentType.INDUCTOR: "Inductor",
                    ComponentType.DIODE: "Diode",
                    ComponentType.LED: "LED",
                    ComponentType.INTEGRATED_CIRCUIT: "IC",
                    ComponentType.CONNECTOR: "Connector",
                    ComponentType.SWITCH: "Switch",
                    ComponentType.TRANSISTOR: "Transistor",
                }
                type_name = type_names.get(analysis["type"], analysis["type"])
                package_text = f" {analysis['package']}" if analysis["package"] else ""
                value_text = f" {comp['value']}" if comp["value"] else ""
                main_desc = f"Component {comp['reference']} from {lib_namespace} is a{value_text}{package_text} {type_name}"

            # Generate issue message
            issue_msg = self._format_issue_message(
                issue, analysis.get("type"), format_type="console"
            )

            return f"{main_desc}\n    Issue: {issue_msg}"

        else:
            raise ValueError(f"Unknown format_type: {format_type}")

    def _format_issue_message(
        self, issue: dict, comp_type: str, format_type: str = "bom"
    ) -> str:
        """Format the issue message based on issue type and output format."""
        issue_type = issue["type"]
        details = issue["details"]

        if issue_type == DiagnosticIssue.TYPE_UNKNOWN:
            if format_type == "console":
                return "Cannot determine component type - may be a non-electronic part (board outline, label, etc.)"
            else:
                return "Component type could not be determined"

        elif issue_type == DiagnosticIssue.NO_TYPE_MATCH:
            comp_type_name = details["comp_type"]
            if format_type == "console":
                type_names = {
                    ComponentType.RESISTOR: "resistor",
                    ComponentType.CAPACITOR: "capacitor",
                    ComponentType.INDUCTOR: "inductor",
                    ComponentType.DIODE: "diode",
                    ComponentType.LED: "led",
                    ComponentType.INTEGRATED_CIRCUIT: "ic",
                    ComponentType.CONNECTOR: "connector",
                    ComponentType.SWITCH: "switch",
                    ComponentType.TRANSISTOR: "transistor",
                }
                friendly_name = type_names.get(comp_type_name, comp_type_name.lower())
                return f"No {friendly_name}s in inventory"
            else:
                return f"No {comp_type_name} components found in inventory"

        elif issue_type == DiagnosticIssue.NO_VALUE_MATCH:
            comp_type_name = details["comp_type"]
            value = details["value"]
            if format_type == "console":
                type_names = {
                    ComponentType.RESISTOR: "resistor",
                    ComponentType.CAPACITOR: "capacitor",
                    ComponentType.INDUCTOR: "inductor",
                    ComponentType.DIODE: "diode",
                    ComponentType.LED: "led",
                    ComponentType.INTEGRATED_CIRCUIT: "ic",
                    ComponentType.CONNECTOR: "connector",
                    ComponentType.SWITCH: "switch",
                    ComponentType.TRANSISTOR: "transistor",
                }
                friendly_name = type_names.get(comp_type_name, comp_type_name.lower())
                return f"No {friendly_name}s with value '{value}' in inventory"
            else:
                return f"No {comp_type_name} components with value {value} found"

        elif issue_type == DiagnosticIssue.PACKAGE_MISMATCH:
            available = ", ".join(details["available_packages"])
            required = details["required_package"]
            value = details["value"]
            return (
                f"Value '{value}' available in {available} packages, but not {required}"
            )

        elif issue_type == DiagnosticIssue.PACKAGE_MISMATCH_GENERIC:
            required = details["required_package"]
            if format_type == "console":
                return f"Package mismatch - needs {required}"
            else:
                return f"Package mismatch - required {required}"

        else:  # no_match
            return "Component specification doesn't match any inventory items"

    def _format_diagnostic_for_bom(self, diagnostic_data: dict) -> str:
        """Format diagnostic data for BOM file output (with DEBUG prefix)"""
        return self._generate_diagnostic_message(diagnostic_data, "bom")

    def _generate_no_match_diagnostics(self, component: Component) -> str:
        """Generate diagnostic information for components with no inventory matches"""
        diagnostic_data = self._analyze_no_match_component(component)
        return self._format_diagnostic_for_bom(diagnostic_data)

    def _analyze_matches(
        self,
        matches: List[Tuple[InventoryItem, int, Optional[str]]],
        best_item: InventoryItem,
        verbose: bool,
    ) -> Tuple[str, List[Tuple[InventoryItem, int]]]:
        """Handle ties: arbitrary choice by default, show ties only with verbose flag"""
        if len(matches) <= 1:
            return "", []

        best_priority = best_item.priority
        tied_items = []

        # Find items that tie with the best priority
        for item, score, _ in matches[1:]:  # Skip the best match, ignore debug info
            if item.priority == best_priority:
                tied_items.append((item, score))

        # Handle ties based on verbose flag
        if tied_items:
            if verbose:
                # Show ties in verbose mode for debugging/transparency
                total_tied = len(tied_items) + 1  # +1 for the best match
                notes = f"Tied priority {best_priority}: {total_tied} options"
                # Limit ALT entries to keep BOM manageable
                return notes, tied_items[:2]
            else:
                # Default: arbitrary choice (use first match), no ALT entries
                return "", []
        else:
            # No ties - single best choice
            return "", []

    def _bom_sort_key(self, entry: BOMEntry) -> Tuple[str, int, str]:
        """Generate sort key for BOM entry: (category, min_component_number, full_reference)"""
        refs = entry.reference.replace("ALT: ", "").split(", ")

        # Extract category and numbers from references
        categories = set()
        min_number = float("inf")

        for ref in refs:
            ref = ref.strip()
            # Extract category (letter prefix) and number
            category, number = self._parse_reference(ref)
            if category:
                categories.add(category)
            if number < min_number:
                min_number = number

        # Use primary category (first alphabetically if mixed)
        primary_category = sorted(categories)[0] if categories else "Z"

        # Handle special case where min_number is still inf (no numbers found)
        if min_number == float("inf"):
            min_number = 0

        return (primary_category, int(min_number), entry.reference)

    def _parse_reference(self, ref: str) -> Tuple[str, float]:
        """Parse reference into category and number: R10 -> ('R', 10), LED4 -> ('LED', 4)"""
        if not ref:
            return "", float("inf")

        # Handle multi-letter prefixes (LED, etc.) and single letters (R, C, etc.)
        match = re.match(r"^([A-Za-z]+)(\d+)$", ref.strip())
        if match:
            category = match.group(1).upper()
            number = float(match.group(2))
            return category, number

        # Fallback for non-standard references
        return ref[0].upper() if ref else "", float("inf")

    def _format_display_value(self, component: Component) -> str:
        # Use EIA-like for R/C/L when possible
        comp_type = get_component_type(component.lib_id, component.footprint)
        if comp_type == ComponentType.RESISTOR:
            ohms = self.matcher._parse_res_to_ohms(component.value)
            if ohms is not None:
                tol = (
                    (component.properties.get(CommonFields.TOLERANCE) or "")
                    .strip()
                    .replace("%", "")
                )
                force0 = False
                try:
                    force0 = float(tol) <= PRECISION_THRESHOLD if tol else False
                except ValueError:
                    force0 = False
                # If schematic explicitly used trailing digit (e.g., 10K0, 47K5), preserve precision intent
                explicit_precision = bool(
                    re.match(r"^\s*\d+[kKmMrR]\d+\s*", component.value or "")
                )
                return self.matcher._ohms_to_eia(
                    ohms, force_trailing_zero=(force0 or explicit_precision)
                )
        if comp_type == ComponentType.CAPACITOR:
            f = self.matcher._parse_cap_to_farad(component.value)
            if f is not None:
                return self.matcher._farad_to_eia(f)
        if comp_type == ComponentType.INDUCTOR:
            h = self.matcher._parse_ind_to_henry(component.value)
            if h is not None:
                return self.matcher._henry_to_eia(h)
        return component.value or ""

    def _group_components(self) -> Dict[str, List[Component]]:
        """Group components by their best matching inventory item"""
        groups = {}

        for component in self.components:
            # Find the best matching inventory item for this component
            matches = self.matcher.find_matches(component)

            if matches:
                # Use the IPN (Internal Part Number) of the best match as the group key
                best_item = matches[0][0]
                key = f"{best_item.ipn}_{component.footprint}"
            else:
                # No matches found - group by original value and footprint as fallback
                key = f"NO_MATCH_{component.value}_{component.footprint}"

            if key not in groups:
                groups[key] = []

            groups[key].append(component)

        return groups
