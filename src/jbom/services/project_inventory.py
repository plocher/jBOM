"""Loader for generating inventory from KiCad project components."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from jbom.common.component_classification import normalize_component_type
from jbom.common.component_id import make_component_id, OPTIONAL_ID_FIELD_DEFS
from jbom.common.types import Component, InventoryItem, DEFAULT_PRIORITY
from jbom.config.defaults import DefaultsConfig, get_defaults
from jbom.common.component_utils import (
    derive_package_from_footprint,
    get_component_type,
)
from jbom.common.constants import CommonFields
from jbom.common.packages import PackageType
from jbom.common.value_parsing import (
    TYPED_PARAMETRIC_COLUMNS_BY_CATEGORY,
    UNCLASSIFIED_CATEGORIES,
    decode_typed_parametric,
)
from jbom.common.synonym_normalization import first_non_empty_alias_value

log = logging.getLogger(__name__)


class ProjectInventoryGenerator:
    """Generates inventory items from project components."""

    def __init__(
        self,
        components: List[Component],
        *,
        cwd: Optional[Path] = None,
    ):
        """Initialize with list of components from schematic.

        Args:
            components: Components loaded from a KiCad schematic.
            cwd: Working directory for project-local profile search.  When
                 ``None``, the built-in generic profile is used.  Pass the
                 project directory to pick up any ``.jbom/`` overrides.
        """
        self.components = components
        self._cwd = cwd
        self._defaults: Optional[DefaultsConfig] = None
        self.inventory: List[InventoryItem] = []
        self.inventory_fields: Set[str] = set()

    def _get_defaults(self) -> DefaultsConfig:
        """Return the loaded defaults profile, loading lazily on first call."""
        if self._defaults is None:
            self._defaults = get_defaults(cwd=self._cwd)
        return self._defaults

    def _classify_all_components(self) -> Dict[int, Optional[str]]:
        """Phase 0+1: classify every component using all available signal sources.

        Returns a mapping of ``id(component)`` → category token (e.g. "LED",
        "RES") or ``None`` when the component cannot be classified.
        """
        log.debug(
            "[classify] Phase 0+1: classifying %d components", len(self.components)
        )
        result: Dict[int, Optional[str]] = {}
        for comp in self.components:
            props = comp.properties or {}
            cat = get_component_type(
                comp.lib_id,
                comp.footprint,
                comp.reference,
                description=props.get("Description", ""),
                keywords=props.get("Keywords", ""),
            )  # None when no signals match
            result[id(comp)] = cat
        n_classified = sum(1 for v in result.values() if v is not None)
        log.debug(
            "[classify] Phase 0+1 complete: %d/%d classified",
            n_classified,
            len(self.components),
        )
        return result

    def _propagate_categories_by_value(
        self, comp_categories: Dict[int, Optional[str]]
    ) -> Dict[int, Optional[str]]:
        """Phase 2: propagate category to unclassified components via value consensus.

        Builds a ``value -> set[category]`` map from already-classified
        components.  For each still-unclassified component whose ``value``
        maps to exactly one category, adopt that category.  Ambiguous values
        (two or more distinct categories) are left unresolved.
        """
        n_unknown = sum(1 for v in comp_categories.values() if v is None)
        log.debug(
            "[classify] Phase 2: value-consensus propagation (%d unknown)", n_unknown
        )
        # Build value → set of categories (ignoring unclassified)
        value_categories: Dict[str, set] = {}
        for comp in self.components:
            cat = comp_categories[id(comp)]
            if cat is None:
                continue
            val = (comp.value or "").strip()
            if val:
                value_categories.setdefault(val, set()).add(cat)

        result: Dict[int, Optional[str]] = dict(comp_categories)
        for comp in self.components:
            if result[id(comp)] is not None:
                continue  # already classified
            val = (comp.value or "").strip()
            cats = value_categories.get(val, set())
            if len(cats) == 1:
                resolved = next(iter(cats))
                result[id(comp)] = resolved
                log.debug(
                    "category propagated by value: %s %r -> %s",
                    comp.reference or comp.lib_id,
                    val,
                    resolved,
                )
        n_promoted = sum(
            1
            for cid, v in result.items()
            if v is not None and comp_categories.get(cid) is None
        )
        log.debug(
            "[classify] Phase 2 complete: %d promoted by value consensus", n_promoted
        )
        return result

    def load(self) -> Tuple[List[InventoryItem], List[str]]:
        """Generate COMPONENT rows from project requirements.

        Returns:
            Tuple of (inventory items list, field names list)
        """
        log.debug(
            "[load] Starting inventory generation for %d components",
            len(self.components),
        )
        # Multi-pass classification: Phase 0+1 (signals) then Phase 2 (value consensus).
        comp_categories = self._propagate_categories_by_value(
            self._classify_all_components()
        )

        # Group by explicit requirement identity so identical requirements collapse.
        grouped_components: Dict[str, List[Component]] = {}

        for comp in self.components:
            key = self._generate_group_key(
                comp, category_override=comp_categories[id(comp)]
            )
            if key not in grouped_components:
                grouped_components[key] = []
            grouped_components[key].append(comp)

        self.inventory = []
        # Standard fields that we always want
        self.inventory_fields = {
            "RowType",
            "ComponentID",
            "IPN",
            "Category",
            "Value",
            "Package",
            "Description",
            "Keywords",
            "Manufacturer",
            "MFGPN",
            "Datasheet",
            "Supplier",
            "SPN",
            "UUID",
            "footprint_full",
            "symbol_lib",
            "symbol_name",
            "ki_keywords",
        }

        for key, comps in grouped_components.items():
            # Use the first component as representative
            representative = comps[0]
            # Collect all UUIDs in the group
            uuids = [c.uuid for c in comps if c.uuid]
            uuid_str = ",".join(uuids)

            item = self._create_inventory_item(
                representative,
                uuid_str,
                category_override=comp_categories[id(representative)],
            )
            self.inventory.append(item)

            # Add any extra fields found in properties
            for prop in representative.properties.keys():
                self.inventory_fields.add(prop)

        # Include typed parametric columns when at least one item has a value.
        for attr, field in (
            ("resistance", "Resistance"),
            ("capacitance", "Capacitance"),
            ("inductance", "Inductance"),
        ):
            if any(getattr(item, attr) is not None for item in self.inventory):
                self.inventory_fields.add(field)

        log.debug(
            "[load] Done: %d unique groups from %d components",
            len(self.inventory),
            len(self.components),
        )
        return self.inventory, sorted(list(self.inventory_fields))

    def load_per_instance(self) -> Tuple[List[InventoryItem], List[str]]:
        """Generate one COMPONENT row per component instance for --per-instance output.

        Returns:
            Tuple of (inventory items list, field names list)
        """
        log.debug(
            "[load_per_instance] Starting for %d components", len(self.components)
        )
        self.inventory = []
        self.inventory_fields = {
            "RowType",
            "ComponentID",
            "IPN",
            "Category",
            "Value",
            "Package",
            "Description",
            "Keywords",
            "Manufacturer",
            "MFGPN",
            "Datasheet",
            "Supplier",
            "SPN",
            "UUID",
            "Footprint",
            "Symbol",
            "footprint_full",
            "symbol_lib",
            "symbol_name",
            "ki_keywords",
        }

        comp_categories = self._propagate_categories_by_value(
            self._classify_all_components()
        )

        for component in self.components:
            item = self._create_inventory_item(
                component,
                component.uuid,
                category_override=comp_categories[id(component)],
            )
            item.raw_data = dict(item.raw_data)
            item.raw_data["Footprint"] = component.footprint
            item.raw_data["Symbol"] = component.lib_id
            item.raw_data["ki_keywords"] = component.properties.get("Keywords", "")

            self.inventory.append(item)
            for prop in component.properties.keys():
                self.inventory_fields.add(prop)

        log.debug("[load_per_instance] Done: %d items", len(self.inventory))
        return self.inventory, sorted(list(self.inventory_fields))

    def _generate_group_key(
        self,
        component: Component,
        category_override: Optional[str] = None,
    ) -> str:
        """Generate deterministic requirement identity via make_component_id().

        Always delegates to ``make_component_id`` — never constructs the
        ComponentID string directly.

        Optional fields (tolerance, voltage, current, wattage, type) are
        filtered by the per-category allowlist from the defaults profile.  When
        a category is not explicitly listed in the profile the full set of
        non-empty optional fields is included (conservative / backward-
        compatible).
        """
        if category_override is None:
            props = component.properties or {}
            category_raw = (
                get_component_type(
                    component.lib_id,
                    component.footprint,
                    component.reference,
                    description=props.get("Description", ""),
                    keywords=props.get("Keywords", ""),
                )
                or "UNK"
            )
        else:
            category_raw = category_override or "UNK"
        category = normalize_component_type(category_raw) or "UNK"
        props = component.properties or {}

        # Raw values for each optional field, keyed by profile_name.
        _raw: Dict[str, str] = {
            "tolerance": props.get(CommonFields.TOLERANCE, props.get("Tolerance", "")),
            "voltage": props.get(CommonFields.VOLTAGE, props.get("Voltage", "")),
            "current": props.get(CommonFields.AMPERAGE, props.get("Amperage", "")),
            "wattage": props.get(CommonFields.WATTAGE, props.get("Wattage", "")),
            "type": props.get("Type", ""),
        }

        # Per-category allowlist: None means "unlisted — include all fields".
        allowed = self._get_defaults().get_component_id_fields(category)

        kwargs: Dict[str, str] = {}
        for field_def in OPTIONAL_ID_FIELD_DEFS:
            raw_val = _raw[field_def.profile_name]
            # Pass the real value when allowed (or when no restriction exists),
            # empty string otherwise — make_component_id omits empty fields.
            kwargs[field_def.param_name] = (
                raw_val
                if (allowed is None or field_def.profile_name in allowed)
                else ""
            )

        return make_component_id(
            category=category,
            value=component.value or "",
            package=self._extract_package(component.footprint),
            **kwargs,
        )

    def _create_inventory_item(
        self,
        component: Component,
        uuid_str: str = "",
        *,
        category_override: Optional[str] = None,
    ) -> InventoryItem:
        """Create an InventoryItem from a Component."""

        # Determine category: use pre-computed override when available so the
        # full multi-pass result is respected; fall back to direct classification.
        if category_override is not None:
            comp_type: Optional[str] = category_override if category_override else None
        else:
            props_early = component.properties or {}
            comp_type = get_component_type(
                component.lib_id,
                component.footprint,
                component.reference,
                description=props_early.get("Description", ""),
                keywords=props_early.get("Keywords", ""),
            )
        category = comp_type if comp_type else "Unknown"

        # Extract package from footprint
        package = self._extract_package(component.footprint)

        # Map properties to InventoryItem fields
        props = component.properties
        # Decode typed parametric fields from schematic properties.
        # props acts as the row: it may carry an explicit Resistance/Capacitance/
        # Inductance property; Value is the fallback.
        row_for_decode: dict[str, str] = dict(props)
        (
            category,
            decode_category,
            category_was_promoted,
        ) = self._resolve_category_for_typed_decode(
            source_category=category,
            row_for_decode=row_for_decode,
            context=f"{component.reference}:{component.lib_id}",
        )

        # IPN must only come from an explicit 'IPN' schematic property.
        # jBOM has no knowledge of IPN structure or naming conventions.
        # Leave blank so the user can assign their own IPNs.
        ipn = props.get("IPN", "")
        # Use the multi-pass category_override when available so the ComponentID
        # reflects the same category that was used to group this component.
        # category_was_promoted is only True for typed-parametric RES/CAP/IND
        # promotion; for LED and other categories promoted by Phase 2 value
        # consensus, category_override carries the correct answer.
        id_category = (
            category_override
            if category_override is not None
            else (category if category_was_promoted else None)
        )
        component_id = self._generate_group_key(
            component,
            category_override=id_category,
        )
        # Parse KiCad lib_id (always NICKNAME:ENTRY_NAME for valid components)
        lib_id_parts = component.lib_id.split(":", 1)
        sym_lib = lib_id_parts[0] if len(lib_id_parts) == 2 else ""
        sym_name = lib_id_parts[1] if len(lib_id_parts) == 2 else lib_id_parts[0]

        return InventoryItem(
            row_type="COMPONENT",
            component_id=component_id,
            ipn=ipn,
            keywords=props.get("Keywords", ""),
            category=category,
            description=props.get(
                "Description", f"{category} {component.value} {package}"
            ),
            smd=props.get("SMD", ""),  # Maybe infer from footprint?
            value=component.value,
            type=props.get("Type", ""),
            tolerance=props.get(CommonFields.TOLERANCE, props.get("Tolerance", "")),
            voltage=props.get(
                CommonFields.VOLTAGE,
                props.get("Voltage", props.get("V", "")),
            ),
            amperage=props.get(
                CommonFields.AMPERAGE,
                props.get("Current", props.get("Amperage", props.get("A", ""))),
            ),
            wattage=props.get(
                CommonFields.WATTAGE,
                props.get("Power", props.get("Wattage", props.get("W", ""))),
            ),
            supplier=props.get("Supplier", ""),
            spn=props.get("SPN", ""),
            manufacturer=self._get_canonical_field_value(
                props,
                canonical="manufacturer",
                fallback_keys=("Manufacturer",),
            ),
            mfgpn=self._get_canonical_field_value(
                props,
                canonical="mpn",
                fallback_keys=("MFGPN", "MPN"),
            ),
            datasheet=props.get("Datasheet", ""),
            package=package,
            uuid=uuid_str,
            priority=DEFAULT_PRIORITY,
            # KiCad harvest fidelity fields
            footprint_full=component.footprint,
            symbol_lib=sym_lib,
            symbol_name=sym_name,
            pins=props.get("Pins", ""),
            pitch=props.get("Pitch", ""),
            resistance=(
                decode_typed_parametric("RES", component.value, row_for_decode)
                if decode_category == "RES"
                else None
            ),
            capacitance=(
                decode_typed_parametric("CAP", component.value, row_for_decode)
                if decode_category == "CAP"
                else None
            ),
            inductance=(
                decode_typed_parametric("IND", component.value, row_for_decode)
                if decode_category == "IND"
                else None
            ),
            source="Project",
            raw_data={
                **props,
                "RowType": "COMPONENT",
                "ComponentID": component_id,
                "footprint_full": component.footprint,
                "symbol_lib": sym_lib,
                "symbol_name": sym_name,
                "ki_keywords": props.get("Keywords", ""),
            },
        )

    def _get_canonical_field_value(
        self,
        row: Dict[str, str],
        *,
        canonical: str,
        fallback_keys: tuple[str, ...] = (),
    ) -> str:
        """Resolve a canonical field value from defaults-profile aliases."""

        keys: list[str] = []
        config = self._get_defaults().get_field_synonym_config(canonical)
        if config is not None:
            keys.extend([config.display_name, *config.synonyms])
        keys.extend(fallback_keys)

        deduped_keys: list[str] = []
        seen: set[str] = set()
        for key in keys:
            normalized = key.strip()
            if not normalized or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            deduped_keys.append(normalized)
        return first_non_empty_alias_value(row, deduped_keys)

    def _resolve_category_for_typed_decode(
        self,
        *,
        source_category: str,
        row_for_decode: Dict[str, str],
        context: str,
    ) -> Tuple[str, Optional[str], bool]:
        """Return (effective_category, decode_category, category_was_promoted)."""

        normalized_category = normalize_component_type(source_category)
        if normalized_category in TYPED_PARAMETRIC_COLUMNS_BY_CATEGORY:
            return source_category, normalized_category, False
        if normalized_category not in UNCLASSIFIED_CATEGORIES:
            return source_category, None, False

        populated_categories = [
            category
            for category, column in TYPED_PARAMETRIC_COLUMNS_BY_CATEGORY.items()
            if str(row_for_decode.get(column, "")).strip()
        ]

        if len(populated_categories) == 1:
            promoted_category = populated_categories[0]
            return promoted_category, promoted_category, True

        if len(populated_categories) > 1:
            populated_columns = ", ".join(
                TYPED_PARAMETRIC_COLUMNS_BY_CATEGORY[category]
                for category in populated_categories
            )
            log.warning(
                "Ambiguous typed parametric promotion for unclassified component '%s': "
                "multiple typed attributes set (%s). Skipping typed decode.",
                context,
                populated_columns,
            )

        return source_category, None, False

    def _extract_package(self, footprint: str) -> str:
        """Extract package name from footprint.

        Tries SMD package pattern matching first for a clean package code
        (e.g. '0603'), then falls back to stripping the library prefix via
        :func:`derive_package_from_footprint`.
        """
        if not footprint:
            return ""

        fp_lower = footprint.lower()

        for pattern in sorted(PackageType.SMD_PACKAGES, key=len, reverse=True):
            if pattern in fp_lower:
                return pattern

        return derive_package_from_footprint(footprint)
