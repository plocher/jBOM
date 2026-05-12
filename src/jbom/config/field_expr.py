"""Field-expression parsing and restricted evaluation for config field references."""

from __future__ import annotations

import ast
import keyword
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping

from jbom.common.fields import normalize_field_name
from jbom.common.types import Diagnostic

if TYPE_CHECKING:
    from jbom.config.field_ref import FieldContext, FieldRefResolver

TransformCallable = Callable[[str], str]


class FieldExpressionError(ValueError):
    """Raised when field-expression parsing or evaluation fails."""


@dataclass(frozen=True)
class TransformCompilationResult:
    """Compiled transform callables and associated diagnostics."""

    transforms: dict[str, TransformCallable]
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True)
class _NamespaceTokenMatch:
    """A scanned `namespace:field` token within an expression string."""

    start_index: int
    end_index: int
    namespace: str
    field_name: str


class FieldExpressionEvaluator:
    """Evaluate field expressions in a restricted namespace."""

    def evaluate(
        self,
        expression: str,
        context: FieldContext,
        *,
        resolver: FieldRefResolver | None = None,
    ) -> str:
        """Evaluate one field expression and return its string value."""

        active_resolver = resolver or self._create_default_resolver()
        raw_expression = str(expression or "").strip()
        if not raw_expression:
            return ""

        rewritten_expression, local_bindings = self._bind_namespaced_tokens(
            raw_expression,
            context,
            active_resolver,
        )

        try:
            expression_ast = ast.parse(rewritten_expression, mode="eval")
        except SyntaxError as exc:
            raise FieldExpressionError(
                f"Invalid field expression: {raw_expression!r}"
            ) from exc

        evaluation_locals: dict[str, Any] = {}
        evaluation_locals.update(active_resolver.expression_transforms(context))
        evaluation_locals.update(local_bindings)
        self._bind_unqualified_names(
            expression_ast,
            evaluation_locals,
            context,
            active_resolver,
        )

        try:
            compiled_expression = compile(
                expression_ast, "<field-expression>", mode="eval"
            )
            evaluated = eval(
                compiled_expression,
                {"__builtins__": {}, "re": re},
                evaluation_locals,
            )
        except Exception as exc:  # pragma: no cover - exception path validated by tests
            raise FieldExpressionError(
                f"Failed to evaluate field expression: {raw_expression!r}"
            ) from exc
        return _coerce_output_value(evaluated)

    def compile_transforms(
        self,
        transforms_stanza: Mapping[str, Any] | None,
        *,
        inherited_transforms: Mapping[str, TransformCallable] | None = None,
        source_name: str = "config",
    ) -> TransformCompilationResult:
        """Validate and compile one `transforms:` mapping into callables."""

        base_registry: dict[str, TransformCallable] = dict(inherited_transforms or {})
        diagnostics: list[Diagnostic] = []
        if transforms_stanza is None:
            return TransformCompilationResult(base_registry, tuple(diagnostics))

        compiled_registry: dict[str, TransformCallable] = dict(base_registry)
        seen_names: set[str] = set()
        for raw_name, raw_transform in transforms_stanza.items():
            transform_name = normalize_field_name(str(raw_name or ""))
            if not transform_name:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        message=(
                            "Transform names must be non-empty strings; "
                            f"got {raw_name!r} in {source_name}"
                        ),
                    )
                )
                continue
            if transform_name in seen_names:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        message=(
                            f"Duplicate transform name {transform_name!r} "
                            f"in {source_name}"
                        ),
                    )
                )
                continue
            seen_names.add(transform_name)

            if transform_name in compiled_registry:
                diagnostics.append(
                    Diagnostic(
                        severity="info",
                        message=(
                            f"NOTICE: transform {transform_name!r} in {source_name} "
                            "shadows an inherited transform"
                        ),
                    )
                )

            expression = self._extract_transform_expression(
                transform_name,
                raw_transform,
                source_name=source_name,
                diagnostics=diagnostics,
            )
            if expression is None:
                continue

            try:
                expression_ast = ast.parse(expression, mode="eval")
                compiled_expression = compile(
                    expression_ast, f"<transform:{transform_name}>", mode="eval"
                )
            except SyntaxError as exc:
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        message=(
                            f"Transform {transform_name!r} in {source_name} has "
                            f"invalid expression syntax: {exc.msg}"
                        ),
                    )
                )
                continue

            compiled_registry[transform_name] = self._compile_transform_callable(
                transform_name=transform_name,
                compiled_expression=compiled_expression,
                transform_registry=compiled_registry,
            )

        return TransformCompilationResult(compiled_registry, tuple(diagnostics))

    def _extract_transform_expression(
        self,
        transform_name: str,
        raw_transform: Any,
        *,
        source_name: str,
        diagnostics: list[Diagnostic],
    ) -> str | None:
        """Extract transform expression text from raw stanza content."""

        if isinstance(raw_transform, str):
            expression = raw_transform.strip()
            if expression:
                return expression
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    message=(
                        f"Transform {transform_name!r} in {source_name} has "
                        "an empty expression"
                    ),
                )
            )
            return None

        if not isinstance(raw_transform, Mapping):
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    message=(
                        f"Transform {transform_name!r} in {source_name} must be "
                        "a string or mapping with an `expr` key"
                    ),
                )
            )
            return None

        expr_value = raw_transform.get("expr")
        if not isinstance(expr_value, str) or not expr_value.strip():
            diagnostics.append(
                Diagnostic(
                    severity="error",
                    message=(
                        f"Transform {transform_name!r} in {source_name} must define "
                        "a non-empty string `expr` value"
                    ),
                )
            )
            return None
        return expr_value.strip()

    def _compile_transform_callable(
        self,
        *,
        transform_name: str,
        compiled_expression: Any,
        transform_registry: Mapping[str, TransformCallable],
    ) -> TransformCallable:
        """Wrap a compiled transform expression into a runtime callable."""

        def _call(value: str) -> str:
            local_namespace: dict[str, Any] = {"value": value}
            local_namespace.update(transform_registry)
            try:
                transformed_value = eval(
                    compiled_expression,
                    {"__builtins__": {}, "re": re},
                    local_namespace,
                )
            except Exception as exc:
                raise FieldExpressionError(
                    f"Failed evaluating transform {transform_name!r} "
                    f"for value {value!r}"
                ) from exc
            return _coerce_output_value(transformed_value)

        return _call

    def _bind_namespaced_tokens(
        self,
        expression: str,
        context: FieldContext,
        resolver: FieldRefResolver,
    ) -> tuple[str, dict[str, str]]:
        """Replace `namespace:field` tokens with bound local variable names."""

        matches = list(self._scan_namespaced_tokens(expression, resolver))
        if not matches:
            return expression, {}

        transformed_expression_parts: list[str] = []
        bound_values: dict[str, str] = {}
        cursor = 0
        for token_index, match in enumerate(matches):
            token_name = f"__jbom_ref_{token_index}"
            transformed_expression_parts.append(expression[cursor : match.start_index])
            transformed_expression_parts.append(token_name)
            cursor = match.end_index

            resolved_value = resolver.resolve_namespaced(
                match.namespace,
                match.field_name,
                context,
            )
            bound_values[token_name] = resolved_value

        transformed_expression_parts.append(expression[cursor:])
        transformed_expression = "".join(transformed_expression_parts)
        return transformed_expression, bound_values

    def _scan_namespaced_tokens(
        self,
        expression: str,
        resolver: FieldRefResolver,
    ) -> Iterable[_NamespaceTokenMatch]:
        """Yield all valid `namespace:field` references outside quoted strings."""

        index = 0
        active_quote: str | None = None
        while index < len(expression):
            character = expression[index]

            if active_quote is not None:
                if character == "\\" and index + 1 < len(expression):
                    index += 2
                    continue
                if character == active_quote:
                    active_quote = None
                index += 1
                continue

            if character in {'"', "'"}:
                active_quote = character
                index += 1
                continue

            if not _is_identifier_start(character):
                index += 1
                continue

            namespace_start = index
            namespace_end = _consume_identifier(expression, namespace_start)
            if namespace_end >= len(expression) or expression[namespace_end] != ":":
                index = namespace_end
                continue

            field_start = namespace_end + 1
            if field_start >= len(expression) or not _is_identifier_start(
                expression[field_start]
            ):
                index = namespace_end
                continue

            field_end = _consume_identifier(expression, field_start)
            if field_end < len(expression) and expression[field_end] == ":":
                index = namespace_end
                continue

            namespace = expression[namespace_start:namespace_end]
            canonical_namespace = resolver.canonical_namespace(namespace)
            if canonical_namespace is None:
                index = field_end
                continue

            field_name = normalize_field_name(expression[field_start:field_end])
            if not field_name:
                index = field_end
                continue

            yield _NamespaceTokenMatch(
                start_index=namespace_start,
                end_index=field_end,
                namespace=canonical_namespace,
                field_name=field_name,
            )
            index = field_end

    def _bind_unqualified_names(
        self,
        expression_ast: ast.Expression,
        evaluation_locals: dict[str, Any],
        context: FieldContext,
        resolver: FieldRefResolver,
    ) -> None:
        """Bind bare field names in expression AST into the eval local namespace."""

        for node in ast.walk(expression_ast):
            if not isinstance(node, ast.Name):
                continue
            identifier = node.id
            if identifier in evaluation_locals:
                continue
            if identifier.startswith("__"):
                continue
            if keyword.iskeyword(identifier):
                continue
            if resolver.has_unqualified_reference(identifier, context):
                evaluation_locals[identifier] = resolver.resolve_unqualified(
                    identifier, context
                )

    def _create_default_resolver(self) -> FieldRefResolver:
        """Create a resolver for direct evaluator usage when none is supplied."""

        from jbom.config.field_ref import FieldRefResolver

        return FieldRefResolver(expression_evaluator=self)


def _is_identifier_start(character: str) -> bool:
    """Return True when `character` can start a Python identifier."""

    return character.isalpha() or character == "_"


def _consume_identifier(text: str, start_index: int) -> int:
    """Consume and return the end index of one identifier token."""

    index = start_index
    while index < len(text) and (text[index].isalnum() or text[index] == "_"):
        index += 1
    return index


def _coerce_output_value(raw_value: object) -> str:
    """Normalize expression results to stable string output values."""

    if isinstance(raw_value, str):
        return raw_value if raw_value.strip() else ""
    if raw_value is None:
        return ""
    if isinstance(raw_value, bool):
        return "Yes" if raw_value else "No"
    return str(raw_value)


__all__ = [
    "FieldExpressionError",
    "FieldExpressionEvaluator",
    "TransformCallable",
    "TransformCompilationResult",
]
