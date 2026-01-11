"""Formatting utilities for generating human-readable reports."""
from typing import Any, Dict, List

def format_coach_agenda(report: Dict[str, Any]) -> str:
    """
    Format a Match Analysis Report into a Coach's Game Review Agenda. 
    """
    if "error" in report:
        return f"Error generating agenda: {report['error']}"

    team_name = report.get("team_name", "Unknown Team")
    series_id = report.get("series_id")
    games = report.get("games", [])
    if not games:
        return "No games found in report."
    
    metadata = report.get("metadata", {})
    opponent = metadata.get("team2") if metadata.get("team1") == team_name else metadata.get("team1", "Opponent")
    
    # Map list
    map_list = ", ".join([g.get("map_name", "Unknown").capitalize() for g in games])
    
    # Extract Metrics for the Agenda (Combined for series)
    key_metrics = report.get("key_metrics", {}).get("team", {})
    economy = key_metrics.get("economy", {})
    pistol = economy.get("pistol", {})
    p_wins = pistol.get("num", 0)
    p_total = pistol.get("denom", 0)
    
    lines = []
    lines.append("=" * 40)
    lines.append("   GENERATED GAME REVIEW AGENDA")
    lines.append("=" * 40)
    lines.append(f"MATCH: {team_name} vs {opponent} (Series {series_id})")
    lines.append(f"MAPS: {map_list}")
    lines.append("-" * 40)
    
    # Summary Section
    lines.append(f"PISTOL PERFORMANCE: {p_wins}/{p_total} rounds won.")
    
    eco_stats = economy.get("eco", {})
    e_wins = eco_stats.get("num", 0)
    e_total = eco_stats.get("denom", 0)
    lines.append(f"ECO CONVERSION: {e_wins}/{e_total} rounds converted.")
    
    openings = key_metrics.get("opening_duels", {})
    fb = openings.get("fb", {}).get("num", 0)
    fd = openings.get("fd", {}).get("num", 0)
    fb_net = openings.get("net_fb", 0)
    lines.append(f"OPENING DUELS: Net {fb_net:+d} (FB: {fb} / FD: {fd})")
    
    clutch = key_metrics.get("impact", {}).get("clutches", {})
    c_wins = clutch.get("wins", 0)
    c_total = clutch.get("attempts", 0)
    lines.append(f"CLUTCH WIN RATE: {c_wins}/{c_total} situations.")
    lines.append("-" * 40)
    
    # Coach's Action Plan (Dynamic Insights)
    lines.append("COACH'S ACTION PLAN:")
    plan_added = False
    
    if fd / (fb + fd + 1e-6) > 0.55:
        lines.append("- IMMEDIATE: Review entry pathing and utility coverage. High FD rate is neutralizing our offensive pressure.")
        plan_added = True
    
    if fb_net < 0:
        lines.append("- STRATEGIC: Practice coordinated trade setups. We are losing too many opening duels without getting trades.")
        plan_added = True
        
    if c_total > 0 and c_wins / c_total < 0.3:
        lines.append("- TACTICAL: Drill post-plant spacing and crossfires. Our conversion in man-disadvantage situations is below baseline.")
        plan_added = True
        
    if not plan_added:
        lines.append("- MAINTAIN: Fundamentals are solid. Focus on specific map counter-stratting for next opponent.")

    lines.append("=" * 40)
    
    return "\n".join(lines)
