"""
Tool fault proxy: match tool calls by name or URL and return fault to apply.

Used by ChaosInterceptor to decide which tool_fault config applies to a given call.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flakestorm.core.config import ToolFaultConfig


def match_tool_fault(
    tool_name: str | None,
    url: str | None,
    fault_configs: list[ToolFaultConfig],
    call_count: int,
) -> ToolFaultConfig | None:
    """
    Return the first fault config that matches this tool call, or None.

    Matching: by tool name (exact or glob *) or by match_url (fnmatch).
    """
    for fc in fault_configs:
        if url and fc.match_url and fnmatch.fnmatch(url, fc.match_url):
            return fc
        if tool_name and (fc.tool == "*" or fnmatch.fnmatch(tool_name, fc.tool)):
            return fc
    return None
