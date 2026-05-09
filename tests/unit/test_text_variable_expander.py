"""Unit tests for jbom.services.text_variable_expander."""

from __future__ import annotations

import re
from datetime import date

from jbom.common.types import TitleBlockMetadata
from jbom.services.text_variable_expander import expand_text_variables


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY_ISO = date.today().isoformat()


def _meta(
    title: str = "",
    revision: str = "",
    date_str: str = "",
    company: str = "",
) -> TitleBlockMetadata:
    return TitleBlockMetadata(
        title=title, revision=revision, date=date_str, company=company
    )


# ---------------------------------------------------------------------------
# Standard title block variables
# ---------------------------------------------------------------------------


class TestKnownVariables:
    def test_title_substituted(self) -> None:
        result = expand_text_variables("${TITLE}", _meta(title="MyBoard"))
        assert result == "MyBoard"

    def test_revision_substituted(self) -> None:
        result = expand_text_variables("${REVISION}", _meta(revision="1.0"))
        assert result == "1.0"

    def test_title_and_revision(self) -> None:
        result = expand_text_variables(
            "${TITLE}_${REVISION}", _meta(title="MyBoard", revision="2.0")
        )
        assert result == "MyBoard_2.0"

    def test_company_substituted(self) -> None:
        result = expand_text_variables("${COMPANY}", _meta(company="Acme"))
        assert result == "Acme"

    def test_date_from_title_block(self) -> None:
        result = expand_text_variables("${DATE}", _meta(date_str="2026-01-15"))
        assert result == "2026-01-15"

    def test_issue_date_alias(self) -> None:
        result = expand_text_variables("${ISSUE_DATE}", _meta(date_str="2026-01-15"))
        assert result == "2026-01-15"

    def test_current_date_is_today(self) -> None:
        result = expand_text_variables("${CURRENT_DATE}", _meta())
        assert result == _TODAY_ISO

    def test_date_falls_back_to_today_when_empty(self) -> None:
        result = expand_text_variables("${DATE}", _meta(date_str=""))
        assert result == _TODAY_ISO

    def test_issue_date_falls_back_to_today_when_empty(self) -> None:
        result = expand_text_variables("${ISSUE_DATE}", _meta(date_str=""))
        assert result == _TODAY_ISO

    def test_multiple_vars_in_complex_template(self) -> None:
        meta = _meta(title="cpNode", revision="1.0", company="SPCoast")
        result = expand_text_variables("${COMPANY}/${TITLE}_${REVISION}", meta)
        assert result == "SPCoast/cpNode_1.0"


# ---------------------------------------------------------------------------
# Empty context (no title block data set)
# ---------------------------------------------------------------------------


class TestEmptyContext:
    def test_empty_title_produces_empty_string(self) -> None:
        result = expand_text_variables("${TITLE}", _meta())
        assert result == ""

    def test_empty_revision_produces_empty_string(self) -> None:
        result = expand_text_variables("${REVISION}", _meta())
        assert result == ""

    def test_template_with_empty_fields_leaves_only_literal(self) -> None:
        result = expand_text_variables("prefix_${REVISION}", _meta())
        assert result == "prefix_"


# ---------------------------------------------------------------------------
# Unknown variables are preserved
# ---------------------------------------------------------------------------


class TestUnknownVariables:
    def test_unknown_var_left_intact(self) -> None:
        result = expand_text_variables("${UNKNOWN}", _meta())
        assert result == "${UNKNOWN}"

    def test_known_and_unknown_mixed(self) -> None:
        result = expand_text_variables("${UNKNOWN}_${TITLE}", _meta(title="Board"))
        assert result == "${UNKNOWN}_Board"

    def test_custom_project_var_preserved(self) -> None:
        """Custom project-level vars (e.g. ${PROJECT_VERSION}) pass through."""
        result = expand_text_variables(
            "${PROJECT_VERSION}_${REVISION}", _meta(revision="2")
        )
        assert result == "${PROJECT_VERSION}_2"


# ---------------------------------------------------------------------------
# Empty and trivial templates
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_template(self) -> None:
        result = expand_text_variables("", _meta(title="X"))
        assert result == ""

    def test_no_variables(self) -> None:
        result = expand_text_variables("static_name", _meta(title="X"))
        assert result == "static_name"

    def test_dollar_without_braces_left_intact(self) -> None:
        result = expand_text_variables("$TITLE", _meta(title="X"))
        assert result == "$TITLE"

    def test_partial_brace_left_intact(self) -> None:
        result = expand_text_variables("${TITLE", _meta(title="X"))
        assert result == "${TITLE"

    def test_current_date_format(self) -> None:
        result = expand_text_variables("${CURRENT_DATE}", _meta())
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result)
