"""Standardized coaching report tools based on agg tables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from vlml.db.manager import EventDatabase

SQL_DIR = Path(__file__).with_name("sql")


@lru_cache(maxsize=None)
def _load_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def _in_clause(values: List[Any]) -> str:
    return ", ".join(["?"] * len(values))


def _confidence_label(rounds: int) -> str:
    if rounds >= 100:
        return "strong"
    if rounds >= 50:
        return "moderate"
    if rounds >= 20:
        return "weak"
    return "insufficient"


def _fetch_series_ids_for_team(
    db: EventDatabase,
    team_name: str,
    last_n_series: int,
) -> List[str]:
    sql = _load_sql("fetch_series_ids_for_team.sql")
    rows = db.query(sql, [f"%{team_name}%", last_n_series])
    return [row[0] for row in rows]


def _fetch_series_ids_for_player(
    db: EventDatabase,
    player_name: str,
    last_n_series: int,
) -> List[str]:
    sql = _load_sql("fetch_series_ids_for_player.sql")
    rows = db.query(sql, [f"%{player_name}%", last_n_series])
    return [row[0] for row in rows]


def _team_round_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND trs.map_name = ?"
        params.append(map_name)

    sql = _load_sql("team_round_metrics.sql").format(
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
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND prs.map_name = ?"
        params.append(map_name)

    sql = _load_sql("team_impact_metrics.sql").format(
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
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND prs.map_name = ?"
        params.append(map_name)

    sql = _load_sql("team_consistency_metrics.sql").format(
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
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND tgs.map_name = ?"
        params.append(map_name)

    pistol_sql = _load_sql("team_economy_pistol.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    pistol_row = db.query(pistol_sql, params)[0]

    eco_sql = _load_sql("team_economy_eco.sql").format(
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


def _assemble_team_metrics(
    db: EventDatabase,
    series_ids: List[str],
    team_name: str,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
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
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{team_name}%"]
    map_filter = ""
    if map_name:
        map_filter = " AND trs.map_name = ?"
        params.append(map_name)

    rounds_sql = _load_sql("round_timeline_rounds.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
    )
    rounds = db.query(rounds_sql, params)
    round_ids = [row[0] for row in rounds]
    if not round_ids:
        return []

    opener_sql = _load_sql("round_timeline_opener.sql").format(
        round_ids_clause=_in_clause(round_ids),
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


def _player_key_metrics(
    db: EventDatabase,
    series_ids: List[str],
    player_name: str,
    map_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids) + [f"%{player_name}%"]
    map_filter = ""
    agent_filter = ""
    if map_name:
        map_filter = " AND prs.map_name = ?"
        params.append(map_name)
    if agent_name:
        agent_filter = " AND prs.agent_name ILIKE ?"
        params.append(f"%{agent_name}%")

    rounds_sql = _load_sql("player_key_metrics.sql").format(
        series_clause=series_clause,
        map_filter=map_filter,
        agent_filter=agent_filter,
    )
    row = db.query(rounds_sql, params)[0]
    rounds_played = row[0] or 0

    return {
        "rounds_played": rounds_played,
        "key_metrics": {
            "opening_duels": {
                "fb": {"num": row[2] or 0, "denom": rounds_played},
                "fd": {"num": row[3] or 0, "denom": rounds_played},
                "net_fb": (row[2] or 0) - (row[3] or 0),
            },
            "conversion": {
                "fb_conv": {"num": 0, "denom": 0},
                "fd_salvage": {"num": 0, "denom": 0},
            },
            "impact": {
                "multikills": {
                    "2k": row[6] or 0,
                    "3k": row[7] or 0,
                    "4k": row[8] or 0,
                    "ace": row[9] or 0,
                },
                "clutches": {
                    "attempts": row[4] or 0,
                    "wins": row[5] or 0,
                    "rate": {"num": row[5] or 0, "denom": row[4] or 0},
                    "avg_difficulty": None,
                },
            },
            "consistency": {
                "kast": {"num": row[12] or 0, "denom": row[13] or 0},
                "adr": {"num": float(row[14]) if row[14] is not None else 0.0, "denom": row[15] or 0},
                "kd": round((row[10] or 0) / (row[11] or 1), 2),
            },
            "economy": {"pistol": {"num": 0, "denom": 0}, "eco": {"num": 0, "denom": 0}, "thrifty": {"count": 0}},
        },
    }


def _series_metadata(db: EventDatabase, series_id: str) -> Dict[str, Any]:
    sql = _load_sql("series_metadata.sql")
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


def _series_games(db: EventDatabase, series_id: str) -> List[Dict[str, Any]]:
    sql = _load_sql("series_games.sql")
    games = db.query(sql, [series_id])

    score_sql = _load_sql("series_games_scores.sql")
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

    sql = _load_sql("team_comparison.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)

    impact_sql = _load_sql("team_comparison_impact.sql").format(map_filter=map_filter)
    impact_rows = db.query(impact_sql, params)
    impact_map = {row[0]: row[1:] for row in impact_rows}

    pistol_sql = _load_sql("team_comparison_pistol.sql").format(map_filter=map_filter)
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
                "adr": {"num": float(row[11]) if row[11] is not None else 0.0, "denom": rounds},
                "kd_ratio": round((row[9] or 0) / (row[10] or 1), 2),
            },
            "timing": {
                "avg_time_to_fk_s": float(row[14]) if row[14] is not None else None,
                "avg_time_to_plant_s": float(row[15]) if row[15] is not None else None,
                "avg_post_plant_duration_s": float(row[16]) if row[16] is not None else None,
            },
            "trades": {
                "deaths_traded": row[12] or 0,
                "deaths_untraded": row[13] or 0,
                "trade_rate": {"num": row[12] or 0, "denom": (row[12] or 0) + (row[13] or 0)},
            },
            "post_plant": {
                "kills": row[17] or 0,
                "deaths": row[18] or 0,
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

    sql = _load_sql("player_performance.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        rounds = row[3] or 0
        deaths = row[5] or 0
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
            "kast_pct": round((row[12] or 0) / (row[13] or 1) * 100, 1),
            "clutch_attempts": row[14] or 0,
            "clutches_won": row[15] or 0,
            "multikills": {
                "2k": row[16] or 0,
                "3k": row[17] or 0,
                "4k": row[18] or 0,
                "ace": row[19] or 0,
            },
        })
    return results


def _kast_impact(
    db: EventDatabase,
    series_id: Optional[str] = None,
    series_ids: Optional[List[str]] = None,
    player_name: Optional[str] = None,
    min_deaths_no_kast: int = 5,
) -> List[Dict[str, Any]]:
    if not series_ids and series_id:
        series_ids = [series_id]
    if not series_ids:
        return []
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids)
    player_filter = ""
    if player_name:
        player_filter = " AND prs.player_name ILIKE ?"
        params.append(f"%{player_name}%")
    sql = _load_sql("kast_impact.sql").format(
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


def _opening_death_impact(
    db: EventDatabase,
    series_id: Optional[str] = None,
    series_ids: Optional[List[str]] = None,
    player_name: Optional[str] = None,
    min_opening_deaths: int = 3,
) -> List[Dict[str, Any]]:
    if not series_ids and series_id:
        series_ids = [series_id]
    if not series_ids:
        return []
    series_clause = _in_clause(series_ids)
    params: List[Any] = list(series_ids)
    player_filter = ""
    if player_name:
        player_filter = " AND prs.player_name ILIKE ?"
        params.append(f"%{player_name}%")
    sql = _load_sql("opening_death_impact.sql").format(
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

    sql = _load_sql("round_timeline_enhanced.sql").format(map_filter=map_filter)
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

    sql = _load_sql("highlight_rounds.sql").format(map_filter=map_filter)
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

    sql = _load_sql("half_breakdown.sql").format(map_filter=map_filter)
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


def _vod_review_priority(
    db: EventDatabase,
    series_id: str,
    map_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [series_id]
    map_filter = ""
    if map_name:
        map_filter = " AND r.map_name = ?"
        params.append(map_name)

    sql = _load_sql("vod_review_priority.sql").format(map_filter=map_filter)
    rows = db.query(sql, params)
    results = []
    for row in rows:
        results.append({
            "game_number": row[0],
            "map_name": row[1],
            "round_number": row[2],
            "reason": row[3],
            "description": f"{row[4]} won FB ({row[5]} -> {row[6]}) but lost the round",
            "focus": "Post-plant positioning and trade timing",
        })
    return results


async def match_analysis_report(
    series_id: str,
    team_name: Optional[str] = None,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a match analysis report for a single series."""
    with EventDatabase(read_only=True) as db:
        metadata = _series_metadata(db, series_id)
        teams_sql = _load_sql("match_analysis_teams.sql")
        team_rows = db.query(teams_sql, [series_id])
        teams = [row[0] for row in team_rows]
        if not teams:
            return {"error": f"No data found for series {series_id}"}

        focus_team = team_name or teams[0]
        opponent_team = next((t for t in teams if t.lower() != focus_team.lower()), None)

        series_scope_sql = _load_sql("match_analysis_scope_rounds.sql")
        scope_rounds = db.query(series_scope_sql, [series_id, f"%{focus_team}%"])[0][0]

        focus_metrics = _assemble_team_metrics(db, [series_id], focus_team, map_name)
        opponent_metrics = _assemble_team_metrics(db, [series_id], opponent_team, map_name) if opponent_team else {}

        return {
            "report_type": "match_analysis",
            "version": "2.0",
            "series_id": series_id,
            "team_name": focus_team,
            "metadata": metadata,
            "games": _series_games(db, series_id),
            "scope": {
                "maps": [map_name] if map_name else list({row[0] for row in db.query(
                    _load_sql("match_analysis_scope_maps.sql"),
                    [series_id],
                )}),
                "rounds": scope_rounds or 0,
                "confidence": _confidence_label(scope_rounds or 0),
            },
            "team_comparison": _team_comparison(db, series_id, map_name),
            "key_metrics": {
                "team": focus_metrics,
                "opponent": opponent_metrics,
            },
            "player_performance": _player_performance(db, series_id, map_name),
            "kast_impact_analysis": _kast_impact(db, series_id),
            "opening_death_impact": _opening_death_impact(db, series_id),
            "round_timeline": _round_timeline_enhanced(db, series_id, map_name),
            "highlight_rounds": _highlight_rounds(db, series_id, map_name),
            "half_breakdown": _half_breakdown(db, series_id, map_name),
            "vod_review_priority": _vod_review_priority(db, series_id, map_name),
        }


async def player_profile_report(
    player_name: str,
    series_ids: Optional[List[str]] = None,
    last_n_series: int = 5,
    map_name: Optional[str] = None,
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a player profile report over multiple series."""
    with EventDatabase(read_only=True) as db:
        if not series_ids:
            series_ids = _fetch_series_ids_for_player(db, player_name, last_n_series)
        if not series_ids:
            return {"error": f"No series found for player {player_name}"}

        series_clause = _in_clause(series_ids)
        params: List[Any] = list(series_ids) + [f"%{player_name}%"]
        map_filter = ""
        agent_filter = ""
        if map_name:
            map_filter = " AND prs.map_name = ?"
            params.append(map_name)
        if agent_name:
            agent_filter = " AND prs.agent_name ILIKE ?"
            params.append(f"%{agent_name}%")

        metadata_sql = _load_sql("player_profile_metadata.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
            agent_filter=agent_filter,
        )
        meta_row = db.query(metadata_sql, params)[0]

        career_sql = _load_sql("player_profile_career.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
            agent_filter=agent_filter,
        )
        career_row = db.query(career_sql, params)[0]

        agent_sql = _load_sql("player_profile_agent.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
            agent_filter=agent_filter,
        )
        agent_rows = db.query(agent_sql, params)

        map_sql = _load_sql("player_profile_map.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
            agent_filter=agent_filter,
        )
        map_rows = db.query(map_sql, params)

        recent_sql = _load_sql("player_profile_recent.sql").format(series_clause=series_clause)
        recent_rows = db.query(recent_sql, list(series_ids) + [f"%{player_name}%"])

        kast_impact = _kast_impact(
            db,
            series_ids=series_ids,
            player_name=player_name,
            min_deaths_no_kast=0,
        )
        od_impact = _opening_death_impact(
            db,
            series_ids=series_ids,
            player_name=player_name,
            min_opening_deaths=0,
        )

        clutch_sql = _load_sql("player_profile_clutch.sql").format(series_clause=series_clause)
        clutch_row = db.query(clutch_sql, params)[0]

        round_type_sql = _load_sql("player_profile_round_types.sql").format(series_clause=series_clause)
        round_type_rows = db.query(round_type_sql, list(series_ids) + [f"%{player_name}%"])

        multikill_sql = _load_sql("player_profile_multikill.sql").format(series_clause=series_clause)
        multikill_row = db.query(multikill_sql, list(series_ids) + [f"%{player_name}%"])[0]

        rounds_played = career_row[9] or 0
        kills = career_row[0] or 0
        deaths = career_row[1] or 0
        fb = career_row[6] or 0
        fd = career_row[7] or 0
        adr = (career_row[3] or 0) / rounds_played if rounds_played > 0 else 0.0
        kast_pct = (career_row[4] or 0) / (career_row[5] or 1) * 100
        win_rate = (career_row[8] or 0) / rounds_played * 100 if rounds_played > 0 else 0.0

        return {
            "report_type": "player_profile",
            "version": "2.0",
            "player_name": player_name,
            "metadata": {
                "player_name": meta_row[0],
                "team_name": meta_row[1],
                "first_game": str(meta_row[2])[:10] if meta_row[2] else None,
                "last_game": str(meta_row[3])[:10] if meta_row[3] else None,
                "total_series": meta_row[4] or 0,
                "total_games": meta_row[5] or 0,
                "total_rounds": meta_row[6] or 0,
            },
            "career_stats": {
                "kills": kills,
                "deaths": deaths,
                "assists": career_row[2] or 0,
                "kd_ratio": round(kills / deaths, 2) if deaths > 0 else float(kills),
                "adr": round(adr, 1),
                "kast_pct": round(kast_pct, 1),
                "fb": fb,
                "fd": fd,
                "fb_pct": round(fb / rounds_played * 100, 1) if rounds_played > 0 else 0.0,
                "fd_pct": round(fd / rounds_played * 100, 1) if rounds_played > 0 else 0.0,
                "rounds_won": career_row[8] or 0,
                "win_rate": round(win_rate, 1),
            },
            "agent_performance": [
                {
                    "agent_name": row[0],
                    "rounds": row[1] or 0,
                    "kills": row[2] or 0,
                    "deaths": row[3] or 0,
                    "kd_ratio": round((row[2] or 0) / (row[3] or 1), 2),
                    "adr": round((row[4] or 0) / (row[1] or 1), 1),
                    "fb": row[5] or 0,
                    "fd": row[6] or 0,
                    "kast_pct": round((row[7] or 0) / (row[8] or 1) * 100, 1),
                    "rounds_won": row[9] or 0,
                    "win_rate": round((row[9] or 0) / (row[1] or 1) * 100, 1),
                }
                for row in agent_rows if row[0]
            ],
            "map_performance": [
                {
                    "map_name": row[0],
                    "rounds": row[1] or 0,
                    "kd_ratio": round((row[2] or 0) / (row[3] or 1), 2),
                    "adr": round((row[4] or 0) / (row[1] or 1), 1),
                    "fb": row[5] or 0,
                    "fd": row[6] or 0,
                    "kast_pct": round((row[7] or 0) / (row[8] or 1) * 100, 1),
                    "win_rate": round((row[9] or 0) / (row[1] or 1) * 100, 1),
                }
                for row in map_rows if row[0]
            ],
            "recent_form": [
                {
                    "series_id": row[0],
                    "date": str(row[1])[:10] if row[1] else None,
                    "opponent": row[2],
                    "result": row[3],
                    "kills": row[4] or 0,
                    "deaths": row[5] or 0,
                    "adr": round((row[6] or 0) / (row[9] or 1), 1),
                    "fb": row[7] or 0,
                    "fd": row[8] or 0,
                }
                for row in recent_rows
            ],
            "kast_impact": (kast_impact[0] if kast_impact else {
                "deaths_without_kast": 0,
                "rounds_lost_when_no_kast": 0,
                "loss_rate_when_no_kast": 0.0,
            }),
            "opening_death_impact": (od_impact[0] if od_impact else {
                "opening_deaths": 0,
                "rounds_won_after_od": 0,
                "rounds_lost_after_od": 0,
                "loss_rate_when_od": 0.0,
            }),
            "clutch_performance": {
                "total_attempts": clutch_row[0] or 0,
                "wins": clutch_row[1] or 0,
                "rate": round((clutch_row[1] or 0) / (clutch_row[0] or 1) * 100, 1),
                "1v1": {"attempts": clutch_row[2] or 0, "wins": clutch_row[3] or 0},
                "1v2": {"attempts": clutch_row[4] or 0, "wins": clutch_row[5] or 0},
                "1v3": {"attempts": clutch_row[6] or 0, "wins": clutch_row[7] or 0},
                "1v4": {"attempts": clutch_row[8] or 0, "wins": clutch_row[9] or 0},
                "1v5": {"attempts": clutch_row[10] or 0, "wins": clutch_row[11] or 0},
            },
            "round_type_performance": {
                row[0]: {
                    "rounds": row[1] or 0,
                    "kills": row[2] or 0,
                    "deaths": row[3] or 0,
                    "kd_ratio": round((row[2] or 0) / (row[3] or 1), 2),
                    "adr": round((row[4] or 0) / (row[1] or 1), 1),
                    "fb": row[5] or 0,
                    "win_rate": round((row[6] or 0) / (row[1] or 1) * 100, 1),
                }
                for row in round_type_rows
            },
            "multikills": {
                "double_kills": multikill_row[0] or 0,
                "triple_kills": multikill_row[1] or 0,
                "quad_kills": multikill_row[2] or 0,
                "aces": multikill_row[3] or 0,
            },
        }


async def scouting_report(
    team_name: str,
    series_ids: Optional[List[str]] = None,
    last_n_series: int = 5,
    map_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a scouting report for a team."""
    with EventDatabase(read_only=True) as db:
        if not series_ids:
            series_ids = _fetch_series_ids_for_team(db, team_name, last_n_series)
        if not series_ids:
            return {"error": f"No series found for team {team_name}"}

        series_clause = _in_clause(series_ids)
        params: List[Any] = list(series_ids) + [f"%{team_name}%"]
        map_filter = ""
        if map_name:
            map_filter = " AND tgs.map_name = ?"
            params.append(map_name)

        metadata_sql = _load_sql("scouting_metadata.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
        )
        meta_row = db.query(metadata_sql, params)[0]

        recent_sql = _load_sql("scouting_recent.sql").format(series_clause=series_clause)
        recent_rows = db.query(
            recent_sql,
            list(series_ids) + [f"%{team_name}%", f"%{team_name}%", f"%{team_name}%"]
        )

        map_pool_sql = _load_sql("scouting_map_pool.sql").format(
            series_clause=series_clause,
            map_filter=map_filter,
        )
        map_rows = db.query(map_pool_sql, params)

        roster_sql = _load_sql("scouting_roster.sql").format(series_clause=series_clause)
        roster_rows = db.query(roster_sql, list(series_ids) + [f"%{team_name}%"])

        agents_sql = _load_sql("scouting_agents.sql").format(series_clause=series_clause)
        agents_rows = db.query(agents_sql, list(series_ids) + [f"%{team_name}%"])

        kast_impact = _kast_impact(db, series_ids=series_ids, min_deaths_no_kast=5) if series_ids else []
        od_impact = _opening_death_impact(db, series_ids=series_ids, min_opening_deaths=3) if series_ids else []

        team_tendencies_sql = _load_sql("scouting_team_tendencies.sql").format(series_clause=series_clause)
        tendencies_row = db.query(team_tendencies_sql, list(series_ids) + [f"%{team_name}%"])[0]

        map_tendencies_sql = _load_sql("scouting_map_tendencies.sql").format(series_clause=series_clause)
        map_tend_rows = db.query(map_tendencies_sql, list(series_ids) + [f"%{team_name}%"])

        comps_sql = _load_sql("scouting_comps.sql").format(series_clause=series_clause)
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
                for row in kast_impact
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
                series_ids = _fetch_series_ids_for_team(db, team_name, last_n_series=20)
            else:
                series_ids = _fetch_series_ids_for_player(db, player_name, last_n_series=20)

        if not series_ids:
            return {"error": "No series found for pattern detection"}

        subject = team_name or player_name or "Unknown"
        if team_name:
            key_metrics = _assemble_team_metrics(db, series_ids, team_name)
            rounds = key_metrics["opening_duels"]["fb"]["denom"]
        else:
            player_metrics = _player_key_metrics(db, series_ids, player_name)
            key_metrics = player_metrics["key_metrics"]
            rounds = player_metrics["rounds_played"]

        return {
            "report_type": "pattern_detection",
            "subject": {"team_name": team_name, "player_name": player_name},
            "scope": {
                "series": len(series_ids),
                "rounds": rounds,
                "confidence": _confidence_label(rounds),
            },
            "summary": {
                "subject": subject,
                "series": len(series_ids),
                "rounds": rounds,
                "confidence": _confidence_label(rounds),
            },
            "key_metrics": key_metrics,
        }
