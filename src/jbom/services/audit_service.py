"""Audit service for jBOM — field quality checks and inventory coverage analysis.

This module is a pure service layer: no argparse imports, no printing, no
subprocess calls.  It may be called directly from the KiCad Python plugin.

Two top-level operations are exposed:

``AuditService.audit_project``
    Given one or more KiCad project paths, check every in-BOM schematic
    component for field quality (local heuristics) and, if an inventory is
    provided, perform a coverage dry-run against that inventory.

``AuditService.audit_inventory``
    Given one or more inventory catalog CSVs, check catalog quality and, if a
    requirements file is provided, report coverage gaps and unused catalog items.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence

from jbom.common.component_classification import get_component_type
from jbom.common.component_filters import apply_component_filters
from jbom.common.field_taxonomy import (
    get_best_practice_fields,
    get_required_fields,
)
from jbom.common.types import Component, InventoryItem
from jbom.services.inventory_reader import InventoryReader
from jbom.services.schematic_reader import SchematicReader
from jbom.services.search.inventory_search_service import InventorySearchService
from jbom.services.sophisticated_inventory_matcher import (
    MatchingOptions,
    SophisticatedInventoryMatcher,
)


# ---------------------------------------------------------------------------
# Public constants / enums
# ---------------------------------------------------------------------------


class CheckType(str, Enum):
    """Type of audit finding.

    PR-1 types
    ----------
    QUALITY_ISSUE
        A field is missing or sub-optimal per the jBOM field taxonomy.
    MATCH_AMBIGUOUS
        Multiple inventory items satisfy all provided attributes exactly.
        The inventory maintainer should add priority values to disambiguate.
    MATCH_HEURISTIC
        A match was found only via heuristics (fuzzy logic).  Specs should
        be tightened or a more-precise inventory item should be added.
    COVERAGE_GAP
        No inventory item matched at all.
    UNUSED_ITEM
        An inventory catalog item was not matched by any project requirement.

    PR-2 stub types (schema reserved, not populated in PR 1)
    --------------------------------------------------------
    SUPPLIER_MISS
        Component was not found in the supplier catalog.
    INVENTORY_GAP
        Component was found in the supplier catalog but is absent from the
        local inventory.
    """

    QUALITY_ISSUE = "QUALITY_ISSUE"
    MATCH_AMBIGUOUS = "MATCH_AMBIGUOUS"
    MATCH_HEURISTIC = "MATCH_HEURISTIC"
    COVERAGE_GAP = "COVERAGE_GAP"
    UNUSED_ITEM = "UNUSED_ITEM"
    SUPPLIER_MISS = "SUPPLIER_MISS"  # PR-2: supplier validation
    INVENTORY_GAP = "INVENTORY_GAP"  # PR-2: supplier validation
    STALE_PART = "STALE_PART"  # existing PN not found in fresh catalog search
    BETTER_AVAILABLE = "BETTER_AVAILABLE"  # fresh search found a different/better PN
    SPEC_MISMATCH = "SPEC_MISMATCH"  # reserved: supplier PN doesn't match item spec


class Severity(str, Enum):
    """Severity level of an audit finding."""

    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"


# ---------------------------------------------------------------------------
# Stable report schema
# ---------------------------------------------------------------------------

#: Ordered CSV column headers for report.csv (stable across PR 1 and PR 2).
REPORT_CSV_COLUMNS: list[str] = [
    "CheckType",
    "Severity",
    "ProjectPath",
    "RefDes",
    "UUID",
    "CatalogFile",
    "IPN",
    "Category",
    "Field",
    "CurrentValue",
    "SuggestedValue",
    "ApprovedValue",  # designer fills in (blank in audit output)
    "Action",  # designer fills in: SET / SKIP / IGNORE / ADD
    "Supplier",  # PR-2
    "SupplierPN",  # PR-2
    "Description",
]


@dataclass(frozen=True)
class AuditRow:
    """One finding row in the audit report.

    All fields that do not apply to a given check type are left as empty
    strings.  The stable column set allows PR-2 to add SUPPLIER_MISS /
    INVENTORY_GAP rows without changing the schema.
    """

    check_type: str
    severity: str
    # Project mode identification
    project_path: str = ""
    ref_des: str = ""
    uuid: str = ""
    # Inventory mode identification
    catalog_file: str = ""
    ipn: str = ""
    # Common
    category: str = ""
    # QUALITY_ISSUE specific
    field: str = ""
    current_value: str = ""
    suggested_value: str = ""
    # Designer-editable columns (blank in audit output; consumer fills in)
    approved_value: str = ""
    action: str = ""
    # Supplier columns (PR-2; blank in PR 1)
    supplier: str = ""
    supplier_pn: str = ""
    # Human description
    description: str = ""

    def to_csv_row(self) -> dict[str, str]:
        """Return a dict keyed by :data:`REPORT_CSV_COLUMNS` for DictWriter."""
        return {
            "CheckType": self.check_type,
            "Severity": self.severity,
            "ProjectPath": self.project_path,
            "RefDes": self.ref_des,
            "UUID": self.uuid,
            "CatalogFile": self.catalog_file,
            "IPN": self.ipn,
            "Category": self.category,
            "Field": self.field,
            "CurrentValue": self.current_value,
            "SuggestedValue": self.suggested_value,
            "ApprovedValue": self.approved_value,
            "Action": self.action,
            "Supplier": self.supplier,
            "SupplierPN": self.supplier_pn,
            "Description": self.description,
        }


@dataclass
class AuditReport:
    """Aggregate result of an audit run.

    Attributes:
        rows: All findings.
        error_count: Number of ERROR-severity rows.
        warn_count: Number of WARN-severity rows.
        info_count: Number of INFO-severity rows.
        exit_code: 0 if no ERROR rows; 1 otherwise.
            Callers passing ``--strict`` should promote non-zero on any WARN.
    """

    rows: list[AuditRow] = field(default_factory=list)
    error_count: int = 0
    warn_count: int = 0
    info_count: int = 0

    @property
    def exit_code(self) -> int:
        """Return 0 when no ERROR rows exist, 1 otherwise."""
        return 1 if self.error_count > 0 else 0

    def exit_code_strict(self) -> int:
        """Return 1 when any WARN or ERROR rows exist (--strict mode)."""
        return 1 if (self.error_count > 0 or self.warn_count > 0) else 0

    def write_csv(self, dest: io.TextIOBase | io.StringIO) -> None:
        """Write the report as CSV to *dest*.

        Args:
            dest: Writable text stream.
        """
        writer = csv.DictWriter(dest, fieldnames=REPORT_CSV_COLUMNS)
        writer.writeheader()
        for row in self.rows:
            writer.writerow(row.to_csv_row())


# ---------------------------------------------------------------------------
# Match quality threshold
# ---------------------------------------------------------------------------

# Minimum score considered an "exact attribute-set match".
# Scoring: type(50) + value(40) = 90. A component providing both type and
# value but no package hint should still reach this threshold for a solid
# catalog item. Matches below this threshold are classified as heuristic.
_EXACT_THRESHOLD = 90


# ---------------------------------------------------------------------------
# AuditService
# ---------------------------------------------------------------------------


class AuditService:
    """Runs field-quality and coverage audits over KiCad projects or inventories.

    This class has no state beyond its construction-time options.  All
    inputs are passed as arguments to :meth:`audit_project` and
    :meth:`audit_inventory`.
    """

    def __init__(self, *, include_debug_info: bool = False) -> None:
        """Create an AuditService.

        Args:
            include_debug_info: When True, pass debug mode to the matcher so
                match debug strings appear in the ``Description`` column.
        """
        self._include_debug_info = include_debug_info
        self._reader = SchematicReader()
        self._matcher = SophisticatedInventoryMatcher(
            MatchingOptions(include_debug_info=include_debug_info)
        )

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def audit_project(
        self,
        project_paths: Sequence[Path],
        inventory_path: Optional[Path] = None,
        project_path_override: Optional[str] = None,
        supplier_service: Optional[InventorySearchService] = None,
        supplier_id: str = "",
    ) -> AuditReport:
        """Audit KiCad project(s) for field quality and optional inventory coverage.

        Args:
            project_paths: Paths to KiCad project directories or schematic files.
            inventory_path: Optional inventory CSV. When provided, a coverage
                dry-run is performed for every in-BOM component.
            project_path_override: When set, this string is used as
                ``ProjectPath`` in every row instead of the resolved path.
                Useful for testing deterministic output.
            supplier_service: Optional :class:`InventorySearchService` instance.
                When provided, every in-BOM component is searched in the
                supplier catalog.
                ``SUPPLIER_MISS`` rows are emitted for components not found.
                ``INVENTORY_GAP`` rows are emitted when a component is found in
                the supplier catalog but absent from *inventory_path* (only when
                *inventory_path* is also provided).
            supplier_id: Display name for the supplier used in row descriptions.

        Returns:
            :class:`AuditReport` with all findings.
        """
        report = AuditReport()

        # Load all components across all project paths.
        components: list[tuple[str, Component]] = []
        for proj_path in project_paths:
            resolved_pro, sch_files = _resolve_project(proj_path)
            pro_str = project_path_override or str(resolved_pro)
            for sch_file in sch_files:
                raw = self._reader.load_components(sch_file)
                filtered = apply_component_filters(
                    raw,
                    {
                        "exclude_dnp": True,
                        "include_only_bom": True,
                        "include_virtual_symbols": False,
                    },
                )
                for comp in filtered:
                    components.append((pro_str, comp))

        # Load inventory for coverage checks (once, outside component loop).
        inventory_items: list[InventoryItem] = []
        if inventory_path is not None:
            reader = InventoryReader(inventory_path)
            all_items, _ = reader.load()
            inventory_items = [i for i in all_items if i.row_type.upper() == "ITEM"]

        for pro_str, comp in components:
            category = (
                get_component_type(comp.lib_id, comp.footprint, comp.reference) or ""
            )

            # --- Local heuristics ---
            for row in self._check_field_quality(comp, category, pro_str):
                report.rows.append(row)
                _increment_counter(report, row.severity)

            # --- Coverage dry-run (only when inventory provided) ---
            if inventory_path is not None:
                match_row = self._classify_coverage(
                    comp, category, pro_str, inventory_items
                )
                if match_row is not None:
                    report.rows.append(match_row)
                    _increment_counter(report, match_row.severity)

            # --- Supplier validation (only when supplier_service provided) ---
            if supplier_service is not None:
                supplier_row = self._check_supplier_coverage(
                    comp,
                    category,
                    pro_str,
                    supplier_service,
                    supplier_id,
                    inventory_items,
                )
                if supplier_row is not None:
                    report.rows.append(supplier_row)
                    _increment_counter(report, supplier_row.severity)

        return report

    def audit_inventory(
        self,
        catalog_paths: Sequence[Path],
        requirements_path: Optional[Path] = None,
        supplier_service: Optional[InventorySearchService] = None,
        supplier_id: str = "",
    ) -> AuditReport:
        """Audit inventory catalog(s) for coverage and quality.

        Args:
            catalog_paths: Paths to inventory CSV catalog files (ITEM rows).
            requirements_path: Optional CSV output of ``jbom inventory proj``
                (COMPONENT rows).  When provided, coverage checks are run
                for each requirement against the catalog.
            supplier_service: Optional :class:`InventorySearchService` instance.
                When provided, each COMPONENT requirement is also checked
                against the supplier catalog.
            supplier_id: Display name for the supplier used in row descriptions.

        Returns:
            :class:`AuditReport` with all findings.
        """
        report = AuditReport()

        # Load catalog ITEM rows.
        catalog_items: list[InventoryItem] = []
        catalog_file_str = str(catalog_paths[0]) if catalog_paths else ""
        for cat_path in catalog_paths:
            reader = InventoryReader(cat_path)
            items, _ = reader.load()
            catalog_items.extend(i for i in items if i.row_type.upper() == "ITEM")

        # No requirements and no supplier check? Nothing to do.
        if requirements_path is None and supplier_service is None:
            return report

        # Freshness checks for ITEM rows (runs even when requirements_path is None).
        if supplier_service is not None:
            for item in catalog_items:
                for freshness_row in self._check_item_freshness(
                    item, catalog_file_str, supplier_service, supplier_id
                ):
                    report.rows.append(freshness_row)
                    _increment_counter(report, freshness_row.severity)

        if requirements_path is None:
            return report

        # Load requirement COMPONENT rows.
        req_reader = InventoryReader(requirements_path)
        all_req, _ = req_reader.load()
        requirements = [r for r in all_req if r.row_type.upper() == "COMPONENT"]

        # Track which catalog items satisfy at least one requirement.
        covered_ipns: set[str] = set()

        for req in requirements:
            category = (req.category or "").strip()
            ref_des = req.component_id or req.uuid or req.ipn
            catalog_file_for_row = catalog_file_str

            match_row = self._classify_inventory_coverage(
                req,
                category,
                ref_des,
                catalog_file_for_row,
                str(requirements_path),
                catalog_items,
                covered_ipns=covered_ipns,
            )
            if match_row is not None:
                report.rows.append(match_row)
                _increment_counter(report, match_row.severity)

            # Supplier validation tier.
            if supplier_service is not None:
                synthetic = _component_from_inventory_item(req)
                supplier_row = self._check_supplier_coverage(
                    synthetic,
                    category,
                    ref_des,
                    supplier_service,
                    supplier_id,
                    catalog_items,
                )
                if supplier_row is not None:
                    report.rows.append(supplier_row)
                    _increment_counter(report, supplier_row.severity)

        # Unused catalog items.
        for item in catalog_items:
            if item.ipn and item.ipn not in covered_ipns:
                row = AuditRow(
                    check_type=CheckType.UNUSED_ITEM,
                    severity=Severity.INFO,
                    catalog_file=catalog_file_str,
                    ipn=item.ipn,
                    category=item.category or "",
                    description=(
                        f"Catalog item {item.ipn!r} was not matched by any project requirement"
                    ),
                )
                report.rows.append(row)
                report.info_count += 1

        return report

    # ------------------------------------------------------------------
    # Private helpers — supplier validation
    # ------------------------------------------------------------------

    def _check_item_freshness(
        self,
        item: InventoryItem,
        catalog_file: str,
        supplier_service: InventorySearchService,
        supplier_id: str,
    ) -> list[AuditRow]:
        """Check whether an ITEM row's existing supplier PN is still current.

        Args:
            item: An ITEM row from the inventory catalog.
            catalog_file: String path to the catalog file (used in rows).
            supplier_service: Search service to query.
            supplier_id: Display name for the supplier.

        Returns:
            Zero or one :class:`AuditRow`: STALE_PART, BETTER_AVAILABLE, or
            nothing (silent when existing PN matches the best result).
        """
        existing_pn = _get_supplier_pn_for_item(item, supplier_id)
        if not existing_pn:
            return []  # SUPPLIER_MISS pathway handles items without PNs

        records = supplier_service.search([item])

        if not records or not records[0].candidates:
            return [
                AuditRow(
                    check_type=CheckType.STALE_PART,
                    severity=Severity.WARN,
                    catalog_file=catalog_file,
                    ipn=item.ipn,
                    category=item.category or "",
                    supplier=supplier_id,
                    supplier_pn=existing_pn,
                    current_value=existing_pn,
                    description=(
                        f"IPN {item.ipn!r}: supplier PN {existing_pn!r} not found by fresh search"
                        + (f" ({supplier_id!r})" if supplier_id else "")
                    ),
                )
            ]

        best = records[0].candidates[0]
        best_pn = best.result.distributor_part_number or ""

        if best_pn and best_pn != existing_pn:
            return [
                AuditRow(
                    check_type=CheckType.BETTER_AVAILABLE,
                    severity=Severity.INFO,
                    catalog_file=catalog_file,
                    ipn=item.ipn,
                    category=item.category or "",
                    supplier=supplier_id,
                    supplier_pn=best_pn,
                    current_value=existing_pn,
                    suggested_value=best_pn,
                    description=(
                        f"IPN {item.ipn!r}: better supplier PN available"
                        + (f" ({supplier_id!r})" if supplier_id else "")
                        + f" — current: {existing_pn!r}, suggested: {best_pn!r}"
                    ),
                )
            ]

        return []  # Silent — existing PN matches best result

    def _check_supplier_coverage(
        self,
        comp: Component,
        category: str,
        pro_str: str,
        search_service: InventorySearchService,
        supplier_id: str,
        inventory_items: list[InventoryItem],
    ) -> Optional[AuditRow]:
        """Search supplier catalog for *comp*; return a finding or ``None``.

        Logic:
        - No candidates → :attr:`CheckType.SUPPLIER_MISS` / ERROR.
        - Candidates found + no local inventory match → :attr:`CheckType.INVENTORY_GAP` / INFO
          (only when *inventory_items* is non-empty).
        - Candidates found + local match (or no inventory to compare) → ``None`` (silent).
        """
        search_item = _component_to_inventory_item(comp, category)
        records = search_service.search([search_item])

        if not records or not records[0].candidates:
            return AuditRow(
                check_type=CheckType.SUPPLIER_MISS,
                severity=Severity.ERROR,
                project_path=pro_str,
                ref_des=comp.reference,
                uuid=comp.uuid,
                category=category,
                supplier=supplier_id,
                description=(
                    f"{comp.reference}: not found in supplier catalog"
                    + (f" ({supplier_id!r})" if supplier_id else "")
                ),
            )

        best = records[0].candidates[0]
        supplier_pn = best.result.distributor_part_number or ""

        # No local inventory to compare against — supplier found, silent.
        if not inventory_items:
            return None

        # Check local inventory.
        comp_ipn = _prop(comp, "IPN")
        comp_mpn = _prop(comp, "MFGPN") or _prop(comp, "MPN")
        if comp_ipn and any(i.ipn == comp_ipn for i in inventory_items):
            return None
        if comp_mpn and any(i.mfgpn == comp_mpn for i in inventory_items):
            return None
        matches = self._matcher.find_matches(comp, inventory_items)
        if matches:
            return None

        return AuditRow(
            check_type=CheckType.INVENTORY_GAP,
            severity=Severity.INFO,
            project_path=pro_str,
            ref_des=comp.reference,
            uuid=comp.uuid,
            category=category,
            supplier=supplier_id,
            supplier_pn=supplier_pn,
            description=(
                f"{comp.reference}: found in supplier catalog"
                + (f" ({supplier_id!r}, PN={supplier_pn!r})" if supplier_pn else "")
                + " but absent from local inventory"
            ),
        )

    # ------------------------------------------------------------------
    # Private helpers — field quality
    # ------------------------------------------------------------------

    def _check_field_quality(
        self,
        comp: Component,
        category: str,
        pro_str: str,
    ) -> list[AuditRow]:
        """Return QUALITY_ISSUE rows for *comp*."""
        rows: list[AuditRow] = []

        # Gather current component properties (include top-level fields).
        present: dict[str, str] = {
            "Value": comp.value or "",
            "Footprint": comp.footprint or "",
        }
        present.update(comp.properties or {})

        # Check required fields.
        for spec in get_required_fields():
            current = present.get(spec.name, "")
            if _is_blank(current):
                rows.append(
                    AuditRow(
                        check_type=CheckType.QUALITY_ISSUE,
                        severity=Severity.ERROR,
                        project_path=pro_str,
                        ref_des=comp.reference,
                        uuid=comp.uuid,
                        category=category,
                        field=spec.name,
                        current_value=current,
                        suggested_value=spec.suggestion,
                        description=f"{comp.reference}: required field '{spec.name}' is missing",
                    )
                )

        # Check best-practice fields.
        for spec in get_best_practice_fields(category):
            current = present.get(spec.name, "")
            if _is_blank(current):
                rows.append(
                    AuditRow(
                        check_type=CheckType.QUALITY_ISSUE,
                        severity=Severity.WARN,
                        project_path=pro_str,
                        ref_des=comp.reference,
                        uuid=comp.uuid,
                        category=category,
                        field=spec.name,
                        current_value=current,
                        suggested_value=spec.suggestion,
                        description=(
                            f"{comp.reference}: best-practice field '{spec.name}' is missing"
                            + (f" — {spec.suggestion}" if spec.suggestion else "")
                        ),
                    )
                )

        return rows

    # ------------------------------------------------------------------
    # Private helpers — coverage classification (project mode)
    # ------------------------------------------------------------------

    def _classify_coverage(
        self,
        comp: Component,
        category: str,
        pro_str: str,
        inventory_items: list[InventoryItem],
    ) -> Optional[AuditRow]:
        """Return a coverage finding for *comp*, or ``None`` if coverage is exact.

        Exclusive attribute check (IPN / MPN) is tried first because these
        provide unambiguous, high-confidence identification that does not need
        scoring.
        """
        if not inventory_items:
            return AuditRow(
                check_type=CheckType.COVERAGE_GAP,
                severity=Severity.ERROR,
                project_path=pro_str,
                ref_des=comp.reference,
                uuid=comp.uuid,
                category=category,
                description=f"{comp.reference}: no inventory items to match against (empty catalog)",
            )

        # --- Exclusive attribute (IPN / MPN) ---
        comp_ipn = _prop(comp, "IPN")
        comp_mpn = _prop(comp, "MFGPN") or _prop(comp, "MPN")
        if comp_ipn:
            if any(i.ipn == comp_ipn for i in inventory_items):
                return None  # exact exclusive match — silent
        if comp_mpn:
            if any(i.mfgpn == comp_mpn for i in inventory_items):
                return None  # exact exclusive match — silent

        # --- Attribute-set matching via SophisticatedInventoryMatcher ---
        matches = self._matcher.find_matches(comp, inventory_items)

        if not matches:
            return AuditRow(
                check_type=CheckType.COVERAGE_GAP,
                severity=Severity.ERROR,
                project_path=pro_str,
                ref_des=comp.reference,
                uuid=comp.uuid,
                category=category,
                description=f"{comp.reference}: no matching inventory item found",
            )

        # Partition into exact vs. heuristic.
        exact = [m for m in matches if m.score >= _EXACT_THRESHOLD]
        heuristic = [m for m in matches if m.score < _EXACT_THRESHOLD]

        if not exact:
            # All matches are heuristic only.
            best = heuristic[0]
            debug = f" (best candidate: {best.inventory_item.ipn}, score={best.score})"
            return AuditRow(
                check_type=CheckType.MATCH_HEURISTIC,
                severity=Severity.WARN,
                project_path=pro_str,
                ref_des=comp.reference,
                uuid=comp.uuid,
                category=category,
                description=(
                    f"{comp.reference}: matched only via heuristics{debug}. "
                    "Tighten specs or add a more precise inventory item."
                ),
            )

        if len(exact) == 1:
            return None  # single exact match — silent

        # Multiple exact candidates — ambiguous.
        candidates = ", ".join(m.inventory_item.ipn for m in exact[:5])
        return AuditRow(
            check_type=CheckType.MATCH_AMBIGUOUS,
            severity=Severity.INFO,
            project_path=pro_str,
            ref_des=comp.reference,
            uuid=comp.uuid,
            category=category,
            description=(
                f"{comp.reference}: {len(exact)} equally-qualified candidates ({candidates}). "
                "Set Priority values in the inventory to disambiguate."
            ),
        )

    # ------------------------------------------------------------------
    # Private helpers — coverage classification (inventory mode)
    # ------------------------------------------------------------------

    def _classify_inventory_coverage(
        self,
        req: InventoryItem,
        category: str,
        ref_des: str,
        catalog_file: str,
        req_file: str,
        catalog_items: list[InventoryItem],
        *,
        covered_ipns: set[str],
    ) -> Optional[AuditRow]:
        """Return a coverage finding for requirement *req*, updating *covered_ipns*.

        A synthetic :class:`Component` is constructed from the COMPONENT row
        so the existing :class:`SophisticatedInventoryMatcher` can be reused
        without modification.
        """
        synthetic = _component_from_inventory_item(req)

        # Exclusive attribute check.
        req_ipn = req.ipn
        if req_ipn:
            matched = [i for i in catalog_items if i.ipn == req_ipn]
            if matched:
                covered_ipns.update(i.ipn for i in matched)
                return None

        matches = self._matcher.find_matches(synthetic, catalog_items)

        if not matches:
            return AuditRow(
                check_type=CheckType.COVERAGE_GAP,
                severity=Severity.ERROR,
                catalog_file=req_file,
                ipn=req_ipn,
                category=category,
                ref_des=ref_des,
                description=f"Requirement {ref_des!r}: no matching catalog item found",
            )

        exact = [m for m in matches if m.score >= _EXACT_THRESHOLD]
        heuristic = [m for m in matches if m.score < _EXACT_THRESHOLD]

        # Mark all matched items as covered.
        for m in matches:
            if m.inventory_item.ipn:
                covered_ipns.add(m.inventory_item.ipn)

        if not exact:
            best = heuristic[0]
            debug = f" (best: {best.inventory_item.ipn}, score={best.score})"
            return AuditRow(
                check_type=CheckType.MATCH_HEURISTIC,
                severity=Severity.WARN,
                catalog_file=req_file,
                ipn=req_ipn,
                category=category,
                ref_des=ref_des,
                description=(
                    f"Requirement {ref_des!r}: matched only via heuristics{debug}. "
                    "Tighten specs or add a more precise catalog item."
                ),
            )

        if len(exact) == 1:
            return None  # single exact match — silent

        candidates = ", ".join(m.inventory_item.ipn for m in exact[:5])
        return AuditRow(
            check_type=CheckType.MATCH_AMBIGUOUS,
            severity=Severity.INFO,
            catalog_file=req_file,
            ipn=req_ipn,
            category=category,
            ref_des=ref_des,
            description=(
                f"Requirement {ref_des!r}: {len(exact)} equally-qualified candidates "
                f"({candidates}). Set Priority values to disambiguate."
            ),
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _is_blank(value: str) -> bool:
    """Return True when a field value is absent or a KiCad no-value sentinel."""
    s = (value or "").strip()
    return s == "" or s == "~"


def _get_supplier_pn_for_item(item: InventoryItem, supplier_id: str) -> str:
    """Return the existing supplier PN stored on an ITEM row.

    Handles LCSC as a special case (``item.lcsc``).  For all other suppliers
    the value is read from ``item.raw_data[supplier.inventory_column]``.

    Args:
        item: An ITEM row from the inventory catalog.
        supplier_id: Normalized supplier ID string (e.g. ``'generic'``).

    Returns:
        Stripped PN string, or empty string when absent.
    """
    from jbom.config.suppliers import resolve_supplier_by_id

    sid = (supplier_id or "").strip().lower()
    if sid == "lcsc":
        return (item.lcsc or "").strip()
    supplier = resolve_supplier_by_id(sid)
    if supplier is None:
        return ""
    return str((item.raw_data or {}).get(supplier.inventory_column, "")).strip()


def _prop(comp: Component, name: str) -> str:
    """Return a component property value, stripping whitespace."""
    return ((comp.properties or {}).get(name) or "").strip()


def _increment_counter(report: AuditReport, severity: str) -> None:
    """Increment the appropriate severity counter on *report*."""
    if severity == Severity.ERROR:
        report.error_count += 1
    elif severity == Severity.WARN:
        report.warn_count += 1
    else:
        report.info_count += 1


def _resolve_project(path: Path) -> tuple[str, list[Path]]:
    """Resolve a project path to (project_path_str, list_of_schematic_files).

    Supports:
    - A directory containing a ``.kicad_pro`` file
    - A ``.kicad_sch`` file directly
    - A ``.kicad_pro`` file

    Returns:
        Tuple of (project canonical string, list of schematic paths to audit).
    """
    from jbom.services.project_file_resolver import ProjectFileResolver

    p = Path(path).resolve()

    if p.is_file() and p.suffix == ".kicad_sch":
        return str(p.parent), [p]

    if p.is_file() and p.suffix == ".kicad_pro":
        resolver = ProjectFileResolver(target_file_type="schematic")
        resolved = resolver.resolve_input(p.parent)
        sch_files = resolved.get_hierarchical_files()
        return str(p), sch_files

    if p.is_dir():
        resolver = ProjectFileResolver(target_file_type="schematic")
        resolved = resolver.resolve_input(p)
        sch_files = resolved.get_hierarchical_files()
        # Try to find .kicad_pro for canonical path
        pro_files = list(p.glob("*.kicad_pro"))
        pro_str = str(pro_files[0]) if pro_files else str(p)
        return pro_str, sch_files

    # Unknown — assume it's a schematic
    return str(p.parent), [p]


def _component_from_inventory_item(item: InventoryItem) -> Component:
    """Build a synthetic :class:`Component` from a COMPONENT inventory row.

    This allows :class:`SophisticatedInventoryMatcher` to be reused for
    inventory-mode coverage checks without any code duplication.
    """
    from jbom.common.types import Component

    # Map InventoryItem fields to Component fields as faithfully as possible.
    props: dict[str, str] = {}
    if item.tolerance:
        props["Tolerance"] = item.tolerance
    if item.voltage:
        props["Voltage"] = item.voltage
    if item.amperage:
        props["Current"] = item.amperage
    if item.wattage:
        props["Power"] = item.wattage
    if item.mfgpn:
        props["MFGPN"] = item.mfgpn
    if item.ipn:
        props["IPN"] = item.ipn

    return Component(
        reference=item.component_id or item.uuid or item.ipn or "",
        lib_id=item.symbol_lib + ":" + item.symbol_name
        if item.symbol_name
        else item.category or "",
        value=item.value or "",
        footprint=item.footprint_full or item.package or "",
        uuid=item.uuid or "",
        properties=props,
    )


__all__ = [
    "CheckType",
    "Severity",
    "AuditRow",
    "AuditReport",
    "AuditService",
    "REPORT_CSV_COLUMNS",
]


def _component_to_inventory_item(comp: Component, category: str) -> InventoryItem:
    """Convert a schematic :class:`Component` to an :class:`InventoryItem` for supplier search.

    Only fields meaningful to :meth:`InventorySearchService.build_query` are
    populated; all others are left as empty strings.
    """
    props = comp.properties or {}
    tolerance = props.get("Tolerance", "")
    voltage = props.get("Voltage", "")
    wattage = props.get("Power", "")
    mfgpn = props.get("MFGPN") or props.get("MPN", "")
    manufacturer = props.get("Manufacturer", "")

    # Simplify footprint: strip KiCad library prefix
    # (e.g. "Resistor_SMD:R_0603" → "R_0603").
    fp = comp.footprint or ""
    package = fp.split(":", 1)[-1] if ":" in fp else fp

    return InventoryItem(
        ipn=props.get("IPN", ""),
        keywords="",
        category=category,
        description="",
        smd="",
        value=comp.value or "",
        type="",
        tolerance=tolerance,
        voltage=voltage,
        amperage="",
        wattage=wattage,
        lcsc="",
        manufacturer=manufacturer,
        mfgpn=mfgpn,
        datasheet="",
        row_type="COMPONENT",
        component_id=comp.reference,
        uuid=comp.uuid,
        package=package,
        raw_data={},
    )
