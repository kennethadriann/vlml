"""Scouting report generation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from vlml.db.manager import EventDatabase

from ..common import (
    fetch_series_ids_for_team,
    in_clause,
    kast_impact,
    load_sql,
    opening_death_impact,
)


async def scouting_report(
    team_name: str,
    series_ids: Optional[List[str]] = None,
    last_n_series: int = 5,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a scouting report for a team."""
    with EventDatabase(read_only=True) as db:
        if not series_ids:
            series_ids = fetch_series_ids_for_team(db, team_name, last_n_series)
        if not series_ids:
            return {"error": f"No series found for team {team_name}"}

        series_clause = in_clause(series_ids)
        params: List[Any] = list(series_ids) + [f"%{team_name}%"]
        map_filter = ""
        if map_name:
            map_filter = " AND tgs.map_name = ?"
            params.append(map_name)

        metadata_sql = load_sql("scouting_metadata.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
        )
        meta_row = db.query(metadata_sql, params)[0]

        recent_sql = load_sql("scouting_recent.sql").format(series_clause=series_clause)
        recent_rows = db.query(
            recent_sql,
            list(series_ids) + [f"%{team_name}%", f"%{team_name}%", f"%{team_name}%"]
        )

        map_pool_sql = load_sql("scouting_map_pool.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
        )
        map_rows = db.query(map_pool_sql, params)

        roster_sql = load_sql("scouting_roster.sql").format(series_clause=series_clause)
        roster_rows = db.query(roster_sql, list(series_ids) + [f"%{team_name}%"])

        agents_sql = load_sql("scouting_agents.sql").format(series_clause=series_clause)
        agents_rows = db.query(agents_sql, list(series_ids) + [f"%{team_name}%"])

        kast_impact_data = kast_impact(db, series_ids=series_ids, min_deaths_no_kast=5) if series_ids else []
        od_impact = opening_death_impact(db, series_ids=series_ids, min_opening_deaths=3) if series_ids else []

        team_tendencies_sql = load_sql("scouting_team_tendencies.sql").format(series_clause=series_clause)
        tendencies_row = db.query(team_tendencies_sql, list(series_ids) + [f"%{team_name}%"])[0]

        map_tendencies_sql = load_sql("scouting_map_tendencies.sql").format(series_clause=series_clause)
        map_tend_rows = db.query(map_tendencies_sql, list(series_ids) + [f"%{team_name}%"])

        comps_sql = load_sql("scouting_comps.sql").format(series_clause=series_clause)
        comps_rows = db.query(comps_sql, list(series_ids) + [f"%{team_name}%"])

        return {
            "report_type": "scouting_report",
            "version": "2.0",
            "team_name": team_name,
            "metadata": {
                "team_name": team_name,
                "series_analyzed": meta_row[0] or 0,
                "games_analyzed": meta_row[1] or 0,
                "rounds_analyzed": meta_row[2] or 0,
            },
            "recent_form": [
                {
                    "series_id": row[0],
                    "date": str(row[1])[:10] if row[1] else None,
                    "tournament": row[2],
                    "opponent": row[3],
                    "result": row[4],
                }
                for row in recent_rows
            ],
            "map_pool": [
                {
                    "map_name": row[0],
                    "games": row[1] or 0,
                    "wins": row[2] or 0,
                    "win_rate": round((row[2] or 0) / (row[1] or 1) * 100, 1),
                }
                for row in map_rows
            ],
            "roster": [
                {
                    "player_name": row[0],
                    "rounds": row[1] or 0,
                    "kills": row[2] or 0,
                    "deaths": row[3] or 0,
                    "kd_ratio": round((row[2] or 0) / (row[3] or 1), 2),
                    "adr": round((row[4] or 0) / (row[1] or 1), 1),
                    "fb": row[5] or 0,
                    "fd": row[6] or 0,
                    "fb_pct": round((row[5] or 0) / (row[1] or 1) * 100, 1),
                    "fd_pct": round((row[6] or 0) / (row[1] or 1) * 100, 1),
                    "kast_pct": round((row[7] or 0) / (row[8] or 1) * 100, 1),
                    "clutches_won": row[9] or 0,
                }
                for row in roster_rows
            ],
            "player_agents": [
                {
                    "player_name": row[0],
                    "agent_name": row[1],
                    "rounds": row[2] or 0,
                    "kd_ratio": round((row[3] or 0) / (row[4] or 1), 2),
                    "adr": round((row[5] or 0) / (row[2] or 1), 1),
                }
                for row in agents_rows if row[1]
            ],
            "kast_impact": [
                {
                    "player_name": row["player_name"],
                    "deaths_without_kast": row["deaths_without_kast"],
                    "rounds_lost_when_no_kast": row["rounds_lost_when_no_kast"],
                    "loss_rate_when_no_kast": row["loss_rate_when_no_kast"],
                }
                for row in kast_impact_data
            ],
            "opening_death_impact": [
                {
                    "player_name": row["player_name"],
                    "opening_deaths": row["opening_deaths"],
                    "rounds_lost_after_od": row["rounds_lost_when_od"],
                    "loss_rate_when_od": row["loss_rate_when_od"],
                }
                for row in od_impact
            ],
            "team_tendencies": {
                "half_performance": {
                    "first_half": {
                        "rounds": tendencies_row[0] or 0,
                        "wins": tendencies_row[1] or 0,
                        "win_rate": round((tendencies_row[1] or 0) / (tendencies_row[0] or 1) * 100, 1),
                    },
                    "second_half": {
                        "rounds": tendencies_row[2] or 0,
                        "wins": tendencies_row[3] or 0,
                        "win_rate": round((tendencies_row[3] or 0) / (tendencies_row[2] or 1) * 100, 1),
                    },
                },
                "pistol": {
                    "rounds": tendencies_row[4] or 0,
                    "wins": tendencies_row[5] or 0,
                    "win_rate": round((tendencies_row[5] or 0) / (tendencies_row[4] or 1) * 100, 1),
                },
                "opening_duels": {
                    "fb": tendencies_row[6] or 0,
                    "fd": tendencies_row[7] or 0,
                    "fb_rate": round(
                        (tendencies_row[6] or 0)
                        / ((tendencies_row[0] or 0) + (tendencies_row[2] or 0) or 1)
                        * 100,
                        1,
                    ),
                    "fd_rate": round(
                        (tendencies_row[7] or 0)
                        / ((tendencies_row[0] or 0) + (tendencies_row[2] or 0) or 1)
                        * 100,
                        1,
                    ),
                },
                "trades": {
                    "deaths_traded": tendencies_row[8] or 0,
                    "deaths_untraded": tendencies_row[9] or 0,
                    "trade_rate": round((tendencies_row[8] or 0) / ((tendencies_row[8] or 0) + (tendencies_row[9] or 1)) * 100, 1),
                },
            },
            "map_tendencies": [
                {
                    "map_name": row[0],
                    "rounds": row[1] or 0,
                    "win_rate": round((row[2] or 0) / (row[1] or 1) * 100, 1),
                    "fb_rate": round((row[3] or 0) / (row[1] or 1) * 100, 1),
                    "avg_time_to_fk_s": float(row[4]) if row[4] is not None else None,
                    "deaths_traded": row[5] or 0,
                    "deaths_untraded": row[6] or 0,
                }
                for row in map_tend_rows
            ],
            "agent_comps": [
                {
                    "map_name": row[0],
                    "comp": (
                        sorted(list(row[1]))
                        if isinstance(row[1], (list, tuple))
                        else [name.strip() for name in (row[1] or "").split(",") if name.strip()]
                    ),
                    "times_played": row[2] or 0,
                    "wins": row[3] or 0,
                }
                for row in comps_rows
            ],
        }
