"""Pattern detection report generation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from vlml.db.manager import EventDatabase

from ..common import (
    confidence_label,
    fetch_series_ids_for_player,
    fetch_series_ids_for_team,
)
from .match_analysis import assemble_team_metrics
from .player_profile import player_key_metrics


async def pattern_detection_report(
    team_name: Optional[str] = None,
    player_name: Optional[str] = None,
    tournament_name: Optional[str] = None,
    series_ids: Optional[List[str]] = None,
    min_rounds: int = 200,
) -> Dict[str, Any]:
    """Detect recurring patterns across a large dataset."""
    if not team_name and not player_name:
        return {"error": "Provide team_name or player_name for pattern detection"}

    with EventDatabase(read_only=True) as db:
        if not series_ids:
            if team_name:
                series_ids = fetch_series_ids_for_team(db, team_name, last_n_series=20)
            else:
                series_ids = fetch_series_ids_for_player(db, player_name, last_n_series=20)

        if not series_ids:
            return {"error": "No series found for pattern detection"}

        subject = team_name or player_name or "Unknown"
        if team_name:
            key_metrics = assemble_team_metrics(db, series_ids, team_name)
            rounds = key_metrics["opening_duels"]["fb"]["denom"]
        else:
            player_metrics = player_key_metrics(db, series_ids, player_name)
            key_metrics = player_metrics["key_metrics"]
            rounds = player_metrics["rounds_played"]

        return {
            "report_type": "pattern_detection",
            "subject": {"team_name": team_name, "player_name": player_name},
            "scope": {
                "series": len(series_ids),
                "rounds": rounds,
                "confidence": confidence_label(rounds),
            },
            "summary": {
                "subject": subject,
                "series": len(series_ids),
                "rounds": rounds,
                "confidence": confidence_label(rounds),
            },
            "key_metrics": key_metrics,
        }
