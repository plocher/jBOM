"""Canonical field-reference parsing and resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from jbom.common.fields import normalize_field_name
from jbom.config.field_expr import (
    FieldExpressionEvaluator,
    TransformCallable,
)
from jbom.config.fields import (
    ANNOTATION_NAMESPACE,
    INV_NAMESPACE,
    JBOM_NAMESPACE,
    PCB_NAMESPACE,
    SCH_NAMESPACE,
    is_jbom_computed,
)

_PLAIN_REFERENCE_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?::[A-Za-z_][A-Za-z0-9_]*)?$"
)

_DEFAULT_SOURCE_PRIORITY: tuple[str, ...] = (
    PCB_NAMESPACE,
    INV_NAMESPACE,
    SCH_NAMESPACE,
)

_SOURCE_NAMESPACE_ALIASES: dict[str, str] = {
    SCH_NAMESPACE: SCH_NAMESPACE,
    PCB_NAMESPACE: PCB_NAMESPACE,
    INV_NAMESPACE: INV_NAMESPACE,
}

_ALL_NAMESPACE_ALIASES: dict[str, str] = {
    SCH_NAMESPACE: SCH_NAMESPACE,
    PCB_NAMESPACE: PCB_NAMESPACE,
    INV_NAMESPACE: INV_NAMESPACE,
    ANNOTATION_NAMESPACE: ANNOTATION_NAMESPACE,
    JBOM_NAMESPACE: JBOM_NAMESPACE,
}


@dataclass
class FieldContext:
    """Field values available while resolving one component row."""

    schematic: Mapping[str, object] = field(default_factory=dict)
    pcb: Mapping[str, object] = field(default_factory=dict)
    inventory: Mapping[str, object] = field(default_factory=dict)
    computed: Mapping[str, object] = field(default_factory=dict)
    annotations: Mapping[str, object] = field(default_factory=dict)
    transforms: Mapping[str, TransformCallable] = field(default_factory=dict)
    source_priority: Sequence[str] = field(
        default_factory=lambda: _DEFAULT_SOURCE_PRIORITY
    )

    def __post_init__(self) -> None:
        self.schematic = _normalize_mapping(self.schematic)
        self.pcb = _normalize_mapping(self.pcb)
        self.inventory = _normalize_mapping(self.inventory)
        self.computed = _normalize_computed_mapping(self.computed)
        self.annotations = _normalize_annotation_mapping(self.annotations)
        self.transforms = _normalize_transform_mapping(self.transforms)
        self.source_priority = _normalize_source_priority(self.source_priority)

    @classmethod
    def from_row_sources(
        cls,
        row_sources: Mapping[str, Mapping[str, object] | None],
        *,
        computed: Mapping[str, object] | None = None,
        annotations: Mapping[str, object] | None = None,
        transforms: Mapping[str, TransformCallable] | None = None,
        source_priority: Sequence[str] | None = None,
    ) -> FieldContext:
        """Construct context from canonical `sch`/`pcb`/`inv` row-source maps."""

        return cls(
            schematic=row_sources.get(SCH_NAMESPACE) or {},
            pcb=row_sources.get(PCB_NAMESPACE) or {},
            inventory=row_sources.get(INV_NAMESPACE) or {},
            computed=computed or {},
            annotations=annotations or {},
            transforms=transforms or {},
            source_priority=source_priority or _DEFAULT_SOURCE_PRIORITY,
        )

    def resolve_source(self, namespace: str, field_name: str) -> str:
        """Resolve one namespaced source field from the context."""

        normalized_namespace = _canonical_source_namespace(namespace)
        if normalized_namespace is None:
            return ""
        source_mapping = self._source_mapping(normalized_namespace)
        return _lookup_normalized_value(source_mapping, field_name)

    def has_source_field(self, namespace: str, field_name: str) -> bool:
        """Return True when a namespaced source field exists in context."""

        normalized_namespace = _canonical_source_namespace(namespace)
        if normalized_namespace is None:
            return False
        source_mapping = self._source_mapping(normalized_namespace)
        return _mapping_has_normalized_key(source_mapping, field_name)

    def resolve_computed(self, field_name: str) -> str:
        """Resolve one jBOM-computed field by canonical name."""

        normalized_field_name = _normalize_jbom_field_name(field_name)
        return _lookup_normalized_value(self.computed, normalized_field_name)

    def has_computed(self, field_name: str) -> bool:
        """Return True when the computed-field value exists in context."""

        normalized_field_name = _normalize_jbom_field_name(field_name)
        return _mapping_has_normalized_key(self.computed, normalized_field_name)

    def resolve_annotation(self, field_name: str) -> str:
        """Resolve one annotation (`ann:*`) field from context."""

        return _lookup_normalized_value(self.annotations, field_name)

    def has_annotation(self, field_name: str) -> bool:
        """Return True when an annotation field exists in context."""

        return _mapping_has_normalized_key(self.annotations, field_name)

    def resolve_unqualified(self, field_name: str) -> str:
        """Resolve one unqualified source field via configured source precedence."""

        for namespace in self.source_priority:
            value = self.resolve_source(namespace, field_name)
            if value:
                return value
        return ""

    def has_unqualified(self, field_name: str) -> bool:
        """Return True when any source has the unqualified field name."""

        return any(
            self.has_source_field(namespace, field_name)
            for namespace in self.source_priority
        )

    def _source_mapping(self, namespace: str) -> Mapping[str, object]:
        """Return source mapping for one canonical namespace."""

        if namespace == SCH_NAMESPACE:
            return self.schematic
        if namespace == PCB_NAMESPACE:
            return self.pcb
        if namespace == INV_NAMESPACE:
            return self.inventory
        return {}


@dataclass(frozen=True)
class FieldRef:
    """One parsed field reference token or expression."""

    namespace: str | None
    field_name: str
    raw_expression: str
    is_expression: bool = False

    @property
    def normalized_reference(self) -> str:
        """Return canonical text for the parsed field reference."""

        if self.is_expression:
            return self.raw_expression
        if self.namespace:
            return f"{self.namespace}:{self.field_name}"
        return self.field_name


class FieldRefResolver:
    """Resolve field references and field expressions against a `FieldContext`."""

    def __init__(
        self,
        *,
        expression_evaluator: FieldExpressionEvaluator | None = None,
        namespace_aliases: Mapping[str, str] | None = None,
        builtin_transforms: Mapping[str, TransformCallable] | None = None,
    ) -> None:
        self._expression_evaluator = expression_evaluator or FieldExpressionEvaluator()
        self._namespace_aliases: dict[str, str] = dict(_ALL_NAMESPACE_ALIASES)
        for alias, namespace in (namespace_aliases or {}).items():
            self._namespace_aliases[normalize_field_name(alias)] = normalize_field_name(
                namespace
            )
        self._builtin_transforms: dict[str, TransformCallable] = dict(
            builtin_transforms or {}
        )

    def parse(self, ref: str) -> FieldRef:
        """Parse a raw field token into a `FieldRef`."""

        raw_ref = str(ref or "").strip()
        if not raw_ref:
            return FieldRef(
                namespace=None, field_name="", raw_expression="", is_expression=False
            )

        if not _PLAIN_REFERENCE_PATTERN.fullmatch(raw_ref):
            return FieldRef(
                namespace=None,
                field_name="",
                raw_expression=raw_ref,
                is_expression=True,
            )

        normalized_ref = normalize_field_name(raw_ref)
        namespace, separator, field_name = normalized_ref.partition(":")
        if separator:
            canonical_namespace = self.canonical_namespace(namespace) or namespace
            return FieldRef(
                namespace=canonical_namespace,
                field_name=normalize_field_name(field_name),
                raw_expression=raw_ref,
                is_expression=False,
            )

        return FieldRef(
            namespace=None,
            field_name=normalized_ref,
            raw_expression=raw_ref,
            is_expression=False,
        )

    def resolve(self, ref: str, context: FieldContext) -> str:
        """Resolve one raw field reference string against context data."""

        raw_ref = str(ref or "").strip()
        if not raw_ref:
            return ""

        parsed_ref = self.parse(raw_ref)
        if parsed_ref.is_expression:
            return self._expression_evaluator.evaluate(
                parsed_ref.raw_expression,
                context,
                resolver=self,
            )

        if parsed_ref.namespace:
            return self.resolve_namespaced(
                parsed_ref.namespace,
                parsed_ref.field_name,
                context,
            )
        return self.resolve_unqualified(parsed_ref.field_name, context)

    def resolve_namespaced(
        self,
        namespace: str,
        field_name: str,
        context: FieldContext,
    ) -> str:
        """Resolve one canonical namespaced field reference."""

        canonical_namespace = self.canonical_namespace(namespace)
        if canonical_namespace is None:
            return ""

        if canonical_namespace == JBOM_NAMESPACE:
            return context.resolve_computed(field_name)

        if canonical_namespace == ANNOTATION_NAMESPACE:
            return context.resolve_annotation(field_name)

        return context.resolve_source(canonical_namespace, field_name)

    def resolve_unqualified(self, field_name: str, context: FieldContext) -> str:
        """Resolve one unqualified field name via computed-then-source precedence."""

        normalized_field_name = normalize_field_name(field_name)
        if context.has_computed(normalized_field_name):
            return context.resolve_computed(normalized_field_name)
        return context.resolve_unqualified(normalized_field_name)

    def has_unqualified_reference(self, field_name: str, context: FieldContext) -> bool:
        """Return True when an unqualified field can be resolved from context."""

        normalized_field_name = normalize_field_name(field_name)
        if is_jbom_computed(normalized_field_name):
            return context.has_computed(normalized_field_name)
        return context.has_unqualified(normalized_field_name)

    def canonical_namespace(self, namespace: str) -> str | None:
        """Return canonical namespace token for an alias, or None when unknown."""

        normalized_namespace = normalize_field_name(namespace)
        if not normalized_namespace:
            return None
        canonical = self._namespace_aliases.get(normalized_namespace)
        if canonical in {
            SCH_NAMESPACE,
            PCB_NAMESPACE,
            INV_NAMESPACE,
            ANNOTATION_NAMESPACE,
            JBOM_NAMESPACE,
        }:
            return canonical
        return None

    def expression_transforms(
        self, context: FieldContext
    ) -> dict[str, TransformCallable]:
        """Return transform functions available during expression evaluation."""

        transforms: dict[str, TransformCallable] = dict(self._builtin_transforms)
        transforms.update(context.transforms)
        return transforms

    def normalize_reference_token(self, ref: str) -> str:
        """Normalize plain field-reference tokens while preserving expressions."""

        parsed_ref = self.parse(ref)
        if parsed_ref.is_expression:
            return str(ref or "").strip()
        return normalize_field_name(str(ref or ""))


def _normalize_mapping(raw_mapping: Mapping[str, object]) -> dict[str, object]:
    """Normalize a raw key/value mapping for field lookup."""

    normalized: dict[str, object] = {}
    for key, value in (raw_mapping or {}).items():
        normalized_key = normalize_field_name(str(key or ""))
        if not normalized_key:
            continue
        normalized[normalized_key] = value
    return normalized


def _normalize_computed_mapping(raw_mapping: Mapping[str, object]) -> dict[str, object]:
    """Normalize computed-field mapping, allowing optional `jbom:` prefixes."""

    normalized: dict[str, object] = {}
    for key, value in (raw_mapping or {}).items():
        normalized_key = normalize_field_name(str(key or ""))
        if not normalized_key:
            continue
        namespace, separator, field_name = normalized_key.partition(":")
        if separator and namespace == JBOM_NAMESPACE:
            normalized[field_name] = value
            continue
        normalized[normalized_key] = value
    return normalized


def _normalize_annotation_mapping(
    raw_mapping: Mapping[str, object]
) -> dict[str, object]:
    """Normalize annotation mapping and allow optional `ann:` key prefix."""

    normalized: dict[str, object] = {}
    for key, value in (raw_mapping or {}).items():
        normalized_key = normalize_field_name(str(key or ""))
        if not normalized_key:
            continue
        namespace, separator, field_name = normalized_key.partition(":")
        if separator and namespace == ANNOTATION_NAMESPACE:
            normalized[field_name] = value
            continue
        normalized[normalized_key] = value
    return normalized


def _normalize_transform_mapping(
    raw_mapping: Mapping[str, TransformCallable],
) -> dict[str, TransformCallable]:
    """Normalize transform mapping keys to canonical identifier form."""

    normalized: dict[str, TransformCallable] = {}
    for key, value in (raw_mapping or {}).items():
        if not callable(value):
            continue
        normalized_key = normalize_field_name(str(key or ""))
        if not normalized_key:
            continue
        normalized[normalized_key] = value
    return normalized


def _normalize_source_priority(priority: Sequence[str]) -> tuple[str, ...]:
    """Normalize source-priority sequence to canonical namespace order."""

    normalized: list[str] = []
    for token in priority:
        canonical = _canonical_source_namespace(token)
        if canonical is None:
            continue
        if canonical in normalized:
            continue
        normalized.append(canonical)
    for fallback_namespace in _DEFAULT_SOURCE_PRIORITY:
        if fallback_namespace in normalized:
            continue
        normalized.append(fallback_namespace)
    return tuple(normalized)


def _canonical_source_namespace(namespace: str) -> str | None:
    """Normalize one namespace token to canonical source namespace form."""

    canonical = _SOURCE_NAMESPACE_ALIASES.get(normalize_field_name(namespace))
    if canonical in {SCH_NAMESPACE, PCB_NAMESPACE, INV_NAMESPACE}:
        return canonical
    return None


def _normalize_jbom_field_name(field_name: str) -> str:
    """Normalize one jBOM field name, accepting optional `jbom:` prefix."""

    normalized = normalize_field_name(field_name)
    namespace, separator, remainder = normalized.partition(":")
    if separator and namespace == JBOM_NAMESPACE:
        return remainder
    return normalized


def _lookup_normalized_value(mapping: Mapping[str, object], field_name: str) -> str:
    """Resolve a normalized field value from a mapping."""

    normalized_name = normalize_field_name(field_name)
    if not normalized_name:
        return ""

    direct_value = _coerce_output_value(mapping.get(normalized_name))
    if direct_value:
        return direct_value

    raw_value = _coerce_output_value(mapping.get(field_name))
    if raw_value:
        return raw_value

    for key, value in mapping.items():
        if normalize_field_name(str(key or "")) != normalized_name:
            continue
        normalized_value = _coerce_output_value(value)
        if normalized_value:
            return normalized_value
    return ""


def _mapping_has_normalized_key(mapping: Mapping[str, object], field_name: str) -> bool:
    """Return True when mapping contains the normalized field key."""

    normalized_name = normalize_field_name(field_name)
    if not normalized_name:
        return False

    if normalized_name in mapping:
        return True
    if field_name in mapping:
        return True
    return any(
        normalize_field_name(str(key or "")) == normalized_name
        for key in mapping.keys()
    )


def _coerce_output_value(raw_value: Any) -> str:
    """Convert raw context values into output field strings."""

    if isinstance(raw_value, str):
        return raw_value if raw_value.strip() else ""
    if raw_value is None:
        return ""
    if isinstance(raw_value, bool):
        return "Yes" if raw_value else "No"
    return str(raw_value)


__all__ = [
    "FieldContext",
    "FieldRef",
    "FieldRefResolver",
]
