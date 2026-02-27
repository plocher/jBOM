"""POS-related step definitions for ultra-simplified pattern (Issue #27).

Legacy step aliases removed - use canonical ultra-simplified steps:
- Given the generic fabricator is selected (Background)
- Given a PCB that contains: (project_centric_steps.py)
- When I run jbom command "pos [options]" (common_steps.py)
- Then the command should succeed/fail (common_steps.py)
- Then the output should contain/not contain "text" (common_steps.py)
- Then a file named "filename" should exist (common_steps.py)
- Then the file "filename" should contain "text" (common_steps.py)
"""
from __future__ import annotations


# Legacy steps removed - use ultra-simplified canonical pattern from common_steps.py
# Only keep truly specialized POS-specific assertions that can't be generalized
