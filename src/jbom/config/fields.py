"""Canonical field namespace and computed-field registry for config references."""

from __future__ import annotations

from jbom.common.fields import normalize_field_name

SCH_NAMESPACE = "sch"
PCB_NAMESPACE = "pcb"
INV_NAMESPACE = "inv"
JBOM_NAMESPACE = "jbom"
ANNOTATION_NAMESPACE = "ann"

SCH = SCH_NAMESPACE
PCB = PCB_NAMESPACE
INV = INV_NAMESPACE
JBOM = JBOM_NAMESPACE
ANN = ANNOTATION_NAMESPACE

JBOM_COMPUTED_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "quantity",
        "fabricator_part_number",
        "smd",
    }
)
JBOM_COMPUTED_FIELD_REFS: frozenset[str] = frozenset(
    f"{JBOM_NAMESPACE}:{field_name}" for field_name in JBOM_COMPUTED_FIELD_NAMES
)

JBOM_QUANTITY_FIELD = f"{JBOM_NAMESPACE}:quantity"
JBOM_FABRICATOR_PART_NUMBER_FIELD = f"{JBOM_NAMESPACE}:fabricator_part_number"
JBOM_SMD_FIELD = f"{JBOM_NAMESPACE}:smd"


def is_jbom_computed(ref: str) -> bool:
    """Return True when *ref* resolves to a known jBOM-computed field."""

    normalized_ref = normalize_field_name(str(ref or ""))
    if not normalized_ref:
        return False

    namespace, separator, field_name = normalized_ref.partition(":")
    if separator:
        return namespace == JBOM_NAMESPACE and field_name in JBOM_COMPUTED_FIELD_NAMES

    return normalized_ref in JBOM_COMPUTED_FIELD_NAMES


__all__ = [
    "ANN",
    "ANNOTATION_NAMESPACE",
    "INV",
    "INV_NAMESPACE",
    "JBOM",
    "JBOM_COMPUTED_FIELD_NAMES",
    "JBOM_COMPUTED_FIELD_REFS",
    "JBOM_FABRICATOR_PART_NUMBER_FIELD",
    "JBOM_NAMESPACE",
    "JBOM_QUANTITY_FIELD",
    "JBOM_SMD_FIELD",
    "PCB",
    "PCB_NAMESPACE",
    "SCH",
    "SCH_NAMESPACE",
    "is_jbom_computed",
]
