"""Backward-compatible re-exports from reports modules.

This module maintains the original import interface for server.py:
    from vlml.tools import insights_tools
    insights_tools.match_analysis_report(...)

The actual implementations are now in:
    - vlml.tools.reports.match_analysis
    - vlml.tools.reports.player_profile
    - vlml.tools.reports.scouting
    - vlml.tools.reports.pattern_detection
"""
from .reports import (
    match_analysis_report,
    pattern_detection_report,
    player_profile_report,
    scouting_report,
)

__all__ = [
    "match_analysis_report",
    "pattern_detection_report",
    "player_profile_report",
    "scouting_report",
]
