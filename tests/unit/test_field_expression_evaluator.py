"""Unit tests for expression evaluation in config field references."""

from __future__ import annotations

import pytest

from jbom.config.field_expr import (
    FieldExpressionError,
    FieldExpressionEvaluator,
)
from jbom.config.field_ref import FieldContext


def test_expression_evaluator_rejects_statement_syntax_in_eval_mode() -> None:
    """Evaluator must reject statements because parser runs in eval-only mode."""

    context = FieldContext()
    evaluator = FieldExpressionEvaluator()

    with pytest.raises(FieldExpressionError) as excinfo:
        evaluator.evaluate("import os", context)

    assert isinstance(excinfo.value.__cause__, SyntaxError)
