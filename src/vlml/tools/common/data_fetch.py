"""Shared data fetching functions for insights reports."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from vlml.db.manager import EventDatabase

from .metrics import in_clause, load_sql


def fetch_series_ids_for_team(
    db: EventDatabase,
    team_name: str,
    last_n_series: int,
) -> List[str]:
    """Fetch recent series IDs for a team."""
    sql = load_sql("fetch_series_ids_for_team.sql")
    rows = db.query(sql, [f"%{team_name}%", last_n_series])
    return [row[0] for row in rows]


def fetch_series_ids_for_player(
    db: EventDatabase,
    player_name: str,
    last_n_series: int,
) -> List[str]:
    """Fetch recent series IDs for a player."""
    sql = load_sql("fetch_series_ids_for_player.sql")
    rows = db.query(sql, [f"%{player_name}%", last_n_series])
    return [row[0] for row in rows]


def series_metadata(db: EventDatabase, series_id: str) -> Dict[str, Any]:
    """Get metadata for a series."""
    sql = load_sql("series_metadata.sql")
    rows = db.query(sql, [series_id])
    if not rows:
        return {}
    row = rows[0]
    return {
        "series_id": row[0],
        "tournament_name": row[1],
        "date": str(row[2])[:10] if row[2] else None,
        "team1": row[3],
        "team2": row[4],
        "winner": row[5],
    }


def series_games(db: EventDatabase, series_id: str) -> List[Dict[str, Any]]:
    """Get games for a series."""
    sql = load_sql("series_games.sql")
    games = db.query(sql, [series_id])

    score_sql = load_sql("series_games_scores.sql")
    score_rows = db.query(score_sql, [series_id])
    scores: Dict[str, Dict[str, int]] = {}
    for game_id, team_name, rounds_won in score_rows:
        scores.setdefault(game_id, {})[team_name] = rounds_won

    results = []
    for game_id, game_number, map_name, winner, total_rounds in games:
        score_map = scores.get(game_id, {})
        if len(score_map) == 2:
            team_names = list(score_map.keys())
            score = f"{score_map[team_names[0]]}-{score_map[team_names[1]]}"
        else:
            score = None
        results.append({
            "game_number": game_number,
            "map_name": map_name,
            "winner": winner,
            "score": score,
            "total_rounds": total_rounds,
        })
    return results


def kast_impact(
    db: EventDatabase,
    series_id: Optional[str] = None,
    series_ids: Optional[List[str]] = None,
    player_name: Optional[str] = None,
    min_deaths_no_kast: int = 5,
) -> List[Dict[str, Any]]:
    """Calculate KAST impact analysis."""
    if not series_ids and series_id:
        series_ids = [series_id]
    if not series_ids:
        return []
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids)
    player_filter = ""
    if player_name:
        player_filter = " AND prs.player_name ILIKE ?"
        params.append(f"%{player_name}%")
    sql = load_sql("kast_impact.sql").format(
        series_clause=series_clause,
        player_filter=player_filter,
    )
    params.append(min_deaths_no_kast)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        denom = row[2] or 0
        num = row[3] or 0
        results.append({
            "player_name": row[0],
            "team_name": row[1],
            "deaths_without_kast": denom,
            "rounds_lost_when_no_kast": num,
            "loss_rate_when_no_kast": round(num / denom * 100, 1) if denom > 0 else 0.0,
        })
    return results


def opening_death_impact(
    db: EventDatabase,
    series_id: Optional[str] = None,
    series_ids: Optional[List[str]] = None,
    player_name: Optional[str] = None,
    min_opening_deaths: int = 3,
) -> List[Dict[str, Any]]:
    """Calculate opening death impact analysis."""
    if not series_ids and series_id:
        series_ids = [series_id]
    if not series_ids:
        return []
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids)
    player_filter = ""
    if player_name:
        player_filter = " AND prs.player_name ILIKE ?"
        params.append(f"%{player_name}%")
    sql = load_sql("opening_death_impact.sql").format(
        series_clause=series_clause,
        player_filter=player_filter,
    )
    params.append(min_opening_deaths)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        denom = row[2] or 0
        lost = row[4] or 0
        results.append({
            "player_name": row[0],
            "team_name": row[1],
            "opening_deaths": denom,
            "rounds_lost_when_od": lost,
            "loss_rate_when_od": round(lost / denom * 100, 1) if denom > 0 else 0.0,
            "rounds_list": row[5] or [],
        })
    return results
