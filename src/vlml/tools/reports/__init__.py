"""Insights report modules."""
from .match_analysis import match_analysis_report
from .pattern_detection import pattern_detection_report
from .player_profile import player_profile_report
from .scouting import scouting_report

__all__ = [
    "match_analysis_report",
    "pattern_detection_report",
    "player_profile_report",
    "scouting_report",
]
