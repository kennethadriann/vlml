"""Match analysis report generation."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from vlml.db.manager import EventDatabase

from ..common import (
    confidence_label,
    in_clause,
    kast_impact,
    load_sql,
    opening_death_impact,
    series_games,
    series_metadata,
)


def _team_round_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND trs.map_name = ?"
        params.append(map_name)

    sql = load_sql("team_round_metrics.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    row = db.query(sql, params)[0]

    return {
        "rounds_played": row[0] or 0,
        "rounds_won": row[1] or 0,
        "first_bloods": row[2] or 0,
        "first_deaths": row[3] or 0,
        "fb_converted_total": row[4] or 0,
        "fb_attempts_total": row[5] or 0,
        "fd_salvage_total": row[6] or 0,
        "fd_attempts_total": row[7] or 0,
    }


def _team_impact_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND prs.map_name = ?"
        params.append(map_name)

    sql = load_sql("team_impact_metrics.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    row = db.query(sql, params)[0]

    return {
        "double_kills": row[0] or 0,
        "triple_kills": row[1] or 0,
        "quad_kills": row[2] or 0,
        "aces": row[3] or 0,
        "clutch_attempts": row[4] or 0,
        "clutch_wins": row[5] or 0,
        "clutch_avg_opponents": float(row[6]) if row[6] is not None else None,
    }


def _team_consistency_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND prs.map_name = ?"
        params.append(map_name)

    sql = load_sql("team_consistency_metrics.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    row = db.query(sql, params)[0]
    kills = row[4] or 0
    deaths = row[5] or 0

    return {
        "kast_num": row[0] or 0,
        "kast_denom": row[1] or 0,
        "adr_num": float(row[2]) if row[2] is not None else 0.0,
        "adr_denom": row[3] or 0,
        "kd_ratio": round(kills / deaths, 2) if deaths > 0 else float(kills),
    }


def _team_economy_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND tgs.map_name = ?"
        params.append(map_name)

    pistol_sql = load_sql("team_economy_pistol.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    pistol_row = db.query(pistol_sql, params)[0]

    eco_sql = load_sql("team_economy_eco.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    eco_row = db.query(eco_sql, params)[0]

    return {
        "pistol_wins": pistol_row[0] or 0,
        "pistol_rounds": pistol_row[1] or 0,
        "eco_rounds": eco_row[0] or 0,
        "eco_wins": eco_row[1] or 0,
        "thrifty_wins": eco_row[2] or 0,
    }


def _build_key_metrics(team_metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "opening_duels": {
            "fb": {"num": team_metrics["first_bloods"], "denom": team_metrics["rounds_played"]},
            "fd": {"num": team_metrics["first_deaths"], "denom": team_metrics["rounds_played"]},
            "net_fb": team_metrics["first_bloods"] - team_metrics["first_deaths"],
        },
        "conversion": {
            "fb_conv": {"num": team_metrics["fb_converted_total"], "denom": team_metrics["fb_attempts_total"]},
            "fd_salvage": {"num": team_metrics["fd_salvage_total"], "denom": team_metrics["fd_attempts_total"]},
        },
        "impact": {
            "multikills": {
                "2k": team_metrics["double_kills"],
                "3k": team_metrics["triple_kills"],
                "4k": team_metrics["quad_kills"],
                "ace": team_metrics["aces"],
            },
            "clutches": {
                "attempts": team_metrics["clutch_attempts"],
                "wins": team_metrics["clutch_wins"],
                "rate": {"num": team_metrics["clutch_wins"], "denom": team_metrics["clutch_attempts"]},
                "avg_difficulty": team_metrics["clutch_avg_opponents"],
            },
        },
        "consistency": {
            "kast": {"num": team_metrics["kast_num"], "denom": team_metrics["kast_denom"]},
            "adr": {"num": team_metrics["adr_num"], "denom": team_metrics["adr_denom"]},
            "kd": team_metrics["kd_ratio"],
        },
        "economy": {
            "pistol": {"num": team_metrics["pistol_wins"], "denom": team_metrics["pistol_rounds"]},
            "eco": {"num": team_metrics["eco_wins"], "denom": team_metrics["eco_rounds"]},
            "thrifty": {"count": team_metrics["thrifty_wins"]},
        },
    }


def assemble_team_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble all team metrics into key metrics structure."""
    round_metrics = _team_round_metrics(db, series_ids, team_name, map_name)
    impact_metrics = _team_impact_metrics(db, series_ids, team_name, map_name)
    consistency_metrics = _team_consistency_metrics(db, series_ids, team_name, map_name)
    economy_metrics = _team_economy_metrics(db, series_ids, team_name, map_name)

    metrics = {
        **round_metrics,
        **impact_metrics,
        **consistency_metrics,
        **economy_metrics,
    }
    return _build_key_metrics(metrics)


def _round_timeline(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    series_clause = in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND trs.map_name = ?"
        params.append(map_name)

    rounds_sql = load_sql("round_timeline_rounds.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    rounds = db.query(rounds_sql, params)
    round_ids = [row[0] for row in rounds]
    if not round_ids:
        return []

    opener_sql = load_sql("round_timeline_opener.sql").format(
        round_ids_clause=in_clause(round_ids),
    )
    opener_rows = db.query(opener_sql, round_ids)
    opener_map = {row[0]: row[1:] for row in opener_rows}

    timeline = []
    for round_id, round_number, map_name_val, round_won in rounds:
        opener_row = opener_map.get(round_id, (None, None, None, None, 0, 0, 0))
        opener, opener_team, victim, victim_team, max_multi, ace_flag, clutch_win = opener_row
        highlight = "Standard"
        if ace_flag:
            highlight = "ACE"
        elif max_multi and max_multi >= 3:
            highlight = "Multi-kill"
        elif clutch_win:
            highlight = "Clutch"

        flag = "STANDARD"
        if opener_team and opener_team.lower() in team_name.lower() and not round_won:
            flag = "REVIEW"
        elif opener_team and opener_team.lower() not in team_name.lower() and round_won:
            flag = "REPLICATE"

        timeline.append({
            "round": int(round_number) if round_number is not None else None,
            "map": map_name_val,
            "opener": opener,
            "opener_victim": victim,
            "winner": team_name if round_won else None,
            "highlight": highlight,
            "flag": flag,
        })

    return timeline


def _issues_from_metrics(team_name: str, key_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []

    fb = key_metrics["opening_duels"]["fb"]
    fd = key_metrics["opening_duels"]["fd"]
    fb_conv = key_metrics["conversion"]["fb_conv"]
    fd_salvage = key_metrics["conversion"]["fd_salvage"]
    clutches = key_metrics["impact"]["clutches"]
    clutch_attempts = clutches.get("attempts", 0)
    clutch_wins = clutches.get("wins", 0)

    if fd["denom"] > 0 and fd["num"] / fd["denom"] > 0.25:
        issues.append({
            "id": len(issues) + 1,
            "title": "High First Death Rate",
            "description": f"{team_name} is dying first too often, putting rounds at an early disadvantage.",
            "evidence": f"First deaths {fd['num']}/{fd['denom']}",
            "frequency": f"{fd['num']} of {fd['denom']} rounds",
            "impact": "Early man disadvantage",
            "root_cause": "Entry timing or insufficient trade setup",
        })

    if fb_conv["denom"] > 0 and fb_conv["num"] / fb_conv["denom"] < 0.55:
        issues.append({
            "id": len(issues) + 1,
            "title": "Low First Blood Conversion",
            "description": f"{team_name} fails to close rounds despite getting first blood.",
            "evidence": f"FB conversion {fb_conv['num']}/{fb_conv['denom']}",
            "frequency": f"{fb_conv['num']} of {fb_conv['denom']} rounds",
            "impact": "Wasted entry advantages",
            "root_cause": "Poor mid-round trading or post-entry spacing",
        })

    if clutch_attempts > 0 and clutch_wins / clutch_attempts < 0.3:
        issues.append({
            "id": len(issues) + 1,
            "title": "Clutch Conversion Below Baseline",
            "description": f"{team_name} is struggling to close clutch situations.",
            "evidence": f"Clutch wins {clutch_wins}/{clutch_attempts}",
            "frequency": f"{clutch_wins} of {clutch_attempts} clutches",
            "impact": "Lost swing rounds",
            "root_cause": "Post-plant setup or isolated fights",
        })

    return issues


def _action_plan_from_issues(issues: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    immediate = []
    short_term = []
    long_term = []

    for issue in issues:
        title = issue["title"].lower()
        if "first death" in title:
            immediate.append("Rehearse entry timing with coordinated utility (flash/recon before first peek).")
        if "conversion" in title:
            short_term.append("Review post-entry protocols to secure trades and avoid solo pushes.")
        if "clutch" in title:
            long_term.append("Build structured post-plant setups to reduce isolated clutch attempts.")

    return {
        "immediate": immediate or ["Review opening duel protocols for consistent trade spacing."],
        "short_term": short_term or ["Standardize mid-round comms for trade-ready spacing."],
        "long_term": long_term or ["Refine default setups to reduce early deaths and improve conversions."],
    }


def _team_comparison(
    db: EventDatabase,
    series_id: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    params: List[Any] = [series_id]
    map_filter = ""
    if map_name:
        map_filter = " AND trs.map_name = ?"
        params.append(map_name)

    sql = load_sql("team_comparison.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)

    impact_sql = load_sql("team_comparison_impact.sql").format(map_filter=map_filter)
    impact_rows = db.query(impact_sql, params)
    impact_map = {row[0]: row[1:] for row in impact_rows}

    pistol_sql = load_sql("team_comparison_pistol.sql").format(map_filter=map_filter)
    pistol_rows = db.query(pistol_sql, params)
    pistol_map = {row[0]: row[1:] for row in pistol_rows}

    comparison = {}
    for row in rows:
        team = row[0]
        impact = impact_map.get(team, (0, 0, 0, 0, 0, 0, 0, 0))
        pistol = pistol_map.get(team, (0, 0, 0, 0))
        rounds = row[1] or 0
        comparison[team] = {
            "name": team,
            "rounds_won": row[2] or 0,
            "rounds_played": rounds,
            "assists": row[11] or 0,
            "opening_duels": {
                "fb": {"num": row[3] or 0, "denom": rounds},
                "fd": {"num": row[4] or 0, "denom": rounds},
                "net_fb": (row[3] or 0) - (row[4] or 0),
            },
            "conversion": {
                "fb_converted": {"num": row[5] or 0, "denom": row[6] or 0},
                "fd_salvaged": {"num": row[7] or 0, "denom": row[8] or 0},
            },
            "impact": {
                "multikills": {
                    "2k": impact[0] or 0,
                    "3k": impact[1] or 0,
                    "4k": impact[2] or 0,
                    "ace": impact[3] or 0,
                },
                "clutches": {
                    "attempts": impact[4] or 0,
                    "wins": impact[5] or 0,
                    "rate": {"num": impact[5] or 0, "denom": impact[4] or 0},
                },
            },
            "consistency": {
                "kast": {"num": impact[6] or 0, "denom": impact[7] or 0},
                "adr": {"num": float(row[12]) if row[12] is not None else 0.0, "denom": rounds},
                "kd_ratio": round((row[9] or 0) / (row[10] or 1), 2),
            },
            "timing": {
                "avg_time_to_fk_s": float(row[15]) if row[15] is not None else None,
                "avg_time_to_plant_s": float(row[16]) if row[16] is not None else None,
                "avg_post_plant_duration_s": float(row[17]) if row[17] is not None else None,
            },
            "trades": {
                "deaths_traded": row[13] or 0,
                "deaths_untraded": row[14] or 0,
                "trade_rate": {"num": row[13] or 0, "denom": (row[13] or 0) + (row[14] or 0)},
            },
            "post_plant": {
                "kills": row[18] or 0,
                "deaths": row[19] or 0,
            },
            "economy": {
                "pistol": {"wins": pistol[0] or 0, "played": pistol[1] or 0},
                "post_pistol": {"wins": pistol[2] or 0, "played": pistol[3] or 0},
            },
        }
    return comparison


def _player_performance(
    db: EventDatabase,
    series_id: str,
    map_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [series_id]
    map_filter = ""
    if map_name:
        map_filter = " AND prs.map_name = ?"
        params.append(map_name)

    sql = load_sql("player_performance.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        rounds = row[3] or 0
        deaths = row[5] or 0
        headshot_hits = row[12] or 0
        hits_total = row[13] or 0
        results.append({
            "player_name": row[0],
            "team_name": row[1],
            "agent_name": row[2],
            "rounds": rounds,
            "kills": row[4] or 0,
            "deaths": deaths,
            "assists": row[6] or 0,
            "kd_ratio": round((row[4] or 0) / deaths, 2) if deaths > 0 else float(row[4] or 0),
            "fb": row[7] or 0,
            "fd": row[8] or 0,
            "opening_kills": row[9] or 0,
            "opening_deaths": row[10] or 0,
            "adr": round((row[11] or 0) / rounds, 1) if rounds > 0 else 0.0,
            "headshot_hits": headshot_hits,
            "hits_total": hits_total,
            "hs_pct": round(headshot_hits / hits_total * 100, 2) if hits_total > 0 else 0.0,
            "kast_pct": round((row[14] or 0) / (row[15] or 1) * 100, 1),
            "clutch_attempts": row[16] or 0,
            "clutches_won": row[17] or 0,
            "multikills": {
                "2k": row[18] or 0,
                "3k": row[19] or 0,
                "4k": row[20] or 0,
                "ace": row[21] or 0,
            },
        })
    return results


def _round_timeline_enhanced(
    db: EventDatabase,
    series_id: str,
    map_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [series_id]
    map_filter = ""
    if map_name:
        map_filter = " AND r.map_name = ?"
        params.append(map_name)

    sql = load_sql("round_timeline_enhanced.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)
    timeline = []
    for row in rows:
        round_number = row[2]
        round_type = "gun"
        if round_number in (1, 13):
            round_type = "pistol"
        elif round_number in (2, 14):
            round_type = "post_pistol"

        timeline.append({
            "game_number": row[0],
            "map_name": row[1],
            "round_number": round_number,
            "round_type": round_type,
            "fb_player": row[5],
            "fb_team": row[6],
            "fd_player": row[7],
            "fd_team": row[8],
            "winner": row[3],
            "end_reason": row[4],
            "time_to_fk_s": float(row[9]) if row[9] is not None else None,
            "time_to_plant_s": float(row[10]) if row[10] is not None else None,
            "post_plant_duration_s": float(row[11]) if row[11] is not None else None,
        })
    return timeline


def _highlight_rounds(
    db: EventDatabase,
    series_id: str,
    map_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [series_id]
    map_filter = ""
    if map_name:
        map_filter = " AND r.map_name = ?"
        params.append(map_name)

    sql = load_sql("highlight_rounds.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        results.append({
            "game_number": row[0],
            "map_name": row[1],
            "round_number": row[2],
            "player": row[3],
            "team": row[4],
            "kills": row[5],
            "type": row[6],
            "clutch_won": bool(row[7]) if row[7] is not None else None,
            "clutch_opponents": row[8],
        })
    return results


def _half_breakdown(
    db: EventDatabase,
    series_id: str,
    map_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [series_id]
    map_filter = ""
    if map_name:
        map_filter = " AND r.map_name = ?"
        params.append(map_name)

    sql = load_sql("half_breakdown.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        results.append({
            "map_name": row[0],
            "team_name": row[1],
            "first_half": {"rounds": row[2] or 0, "wins": row[3] or 0},
            "second_half": {"rounds": row[4] or 0, "wins": row[5] or 0},
        })
    return results


async def match_analysis_report(
    series_id: str,
    team_name: Optional[str] = None,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a match analysis report for a single series."""
    with EventDatabase(read_only=True) as db:
        metadata = series_metadata(db, series_id)
        teams_sql = load_sql("match_analysis_teams.sql")
        team_rows = db.query(teams_sql, [series_id])
        teams = [row[0] for row in team_rows]
        if not teams:
            return {"error": f"No data found for series {series_id}"}

        focus_team = team_name or teams[0]
        opponent_team = next((t for t in teams if t.lower() != focus_team.lower()), None)

        series_scope_sql = load_sql("match_analysis_scope_rounds.sql")
        scope_rounds = db.query(series_scope_sql, [series_id, f"%{focus_team}%"])[0][0]

        focus_metrics = assemble_team_metrics(db, [series_id], focus_team, map_name)
        opponent_metrics = assemble_team_metrics(db, [series_id], opponent_team, map_name) if opponent_team else {}

        return {
            "report_type": "match_analysis",
            "version": "2.0",
            "series_id": series_id,
            "team_name": focus_team,
            "metadata": metadata,
            "games": series_games(db, series_id),
            "scope": {
                "maps": [map_name] if map_name else list({row[0] for row in db.query(
                    load_sql("match_analysis_scope_maps.sql"),
                    [series_id],
                )}),
                "rounds": scope_rounds or 0,
                "confidence": confidence_label(scope_rounds or 0),
            },
            "team_comparison": _team_comparison(db, series_id, map_name),
            "key_metrics": {
                "team": focus_metrics,
                "opponent": opponent_metrics,
            },
            "player_performance": _player_performance(db, series_id, map_name),
            "kast_impact_analysis": kast_impact(db, series_id),
            "opening_death_impact": opening_death_impact(db, series_id),
            "round_timeline": _round_timeline_enhanced(db, series_id, map_name),
            "highlight_rounds": _highlight_rounds(db, series_id, map_name),
            "half_breakdown": _half_breakdown(db, series_id, map_name),
        }
