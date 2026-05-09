"""Text variable expansion for KiCad archive naming templates.

Expands the standard KiCad title block variables found in template strings
such as ``"${TITLE}_${REVISION}"``.  The variable set mirrors the variables
available in KiCad's own ``pcbnew.ExpandTextVars()`` for the title block
stanza:

``${TITLE}``
    Project title from the title block (empty string when not set).
``${REVISION}``
    Revision string from the title block (empty string when not set).
``${DATE}`` / ``${ISSUE_DATE}``
    Issue date from the title block (e.g. ``"2026-05-09"``).  Falls back to
    today's ISO date when the title block date is absent.
``${CURRENT_DATE}``
    Always today's ISO date, regardless of the title block value.
``${COMPANY}``
    Company / organisation from the title block (empty string when not set).

Any ``${VARIABLE}`` tokens not in the list above are left unchanged so that
future KiCad variables or project-level custom variables pass through without
being silently dropped.  The plugin adapter can run ``pcbnew.ExpandTextVars()``
first to resolve custom project variables, then pass the result here for
title-block substitution — or vice-versa.

Usage::

    from jbom.common.types import TitleBlockMetadata
    from jbom.services.text_variable_expander import expand_text_variables

    meta = TitleBlockMetadata(title="MyBoard", revision="1.0")
    stem = expand_text_variables("${TITLE}_${REVISION}", meta)
    # → "MyBoard_1.0"
"""

from __future__ import annotations

import re
from datetime import date as _date

from jbom.common.types import TitleBlockMetadata

__all__ = ["expand_text_variables"]


def expand_text_variables(
    template: str,
    metadata: TitleBlockMetadata,
) -> str:
    """Expand KiCad title block text variables in *template*.

    Args:
        template: Template string, e.g. ``"${TITLE}_${REVISION}"``.
        metadata: Resolved title block values read from the KiCad project.

    Returns:
        String with known ``${VAR}`` tokens substituted.  Unknown tokens are
        left unchanged so callers can detect unexpanded variables.

    Example::

        meta = TitleBlockMetadata(title="cpNode", revision="1.0",
                                   date="2026-05-09", company="SPCoast")
        expand_text_variables("${TITLE}_${REVISION}", meta)
        # → "cpNode_1.0"
        expand_text_variables("${COMPANY}/${TITLE}_${REVISION}", meta)
        # → "SPCoast/cpNode_1.0"
        expand_text_variables("${UNKNOWN}_${TITLE}", meta)
        # → "${UNKNOWN}_cpNode"  ← unknown var preserved
    """
    today = _date.today().isoformat()
    substitutions: dict[str, str] = {
        "TITLE": metadata.title,
        "REVISION": metadata.revision,
        "DATE": metadata.date or today,
        "ISSUE_DATE": metadata.date or today,
        "CURRENT_DATE": today,
        "COMPANY": metadata.company,
    }

    def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
        key = match.group(1)
        # Return the substitution when known; leave the token intact otherwise.
        return substitutions[key] if key in substitutions else match.group(0)

    return re.sub(r"\$\{([^}]+)\}", _replace, template)
