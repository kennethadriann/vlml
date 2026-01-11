"""Tools for predicting match outcomes and 'what if' scenarios."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from vlml.db.manager import EventDatabase


async def predict_retake_win_probability(
    map_name: str,
    attackers_alive: int,
    defenders_alive: int,
    site: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Predict the probability of a successful retake (Defenders winning after plant).
    
    Args:
        map_name: Name of the map (e.g., 'Haven', 'Ascent')
        attackers_alive: Number of attackers alive at plant time.
        defenders_alive: Number of defenders alive at plant time.
        site: Optional bombsite (currently unused due to data availability).
    """
    with EventDatabase(read_only=True) as db:
        # Optimized query using pre-joined rounds and base_events
        sql = """
        WITH plant_events AS (
            SELECT
                be.round_id,
                be.occurred_at as plant_time,
                be.actor_team_name as attacking_team
            FROM base_events be
            WHERE be.event_type = 'player-completed-plantBomb'
              AND be.map_name ILIKE ?
        ),
        deaths_before_plant AS (
            SELECT
                d.round_id,
                d.target_team_name,
                COUNT(*) as deaths
            FROM base_events d
            INNER JOIN plant_events p ON d.round_id = p.round_id
            WHERE (d.event_type LIKE 'player-%killed-player')
              AND d.occurred_at < p.plant_time
            GROUP BY d.round_id, d.target_team_name
        ),
        situations AS (
            SELECT
                r.round_id,
                (r.winning_team_name != p.attacking_team) as retake_success,
                (5 - COALESCE(da.deaths, 0)) as att_alive,
                (5 - COALESCE(dd.deaths, 0)) as def_alive
            FROM plant_events p
            INNER JOIN rounds r ON p.round_id = r.round_id
            LEFT JOIN deaths_before_plant da ON p.round_id = da.round_id AND da.target_team_name = p.attacking_team
            LEFT JOIN deaths_before_plant dd ON p.round_id = dd.round_id AND dd.target_team_name != p.attacking_team
        )
        SELECT
            COUNT(*) as sample_size,
            AVG(CASE WHEN retake_success THEN 1.0 ELSE 0.0 END) as win_rate
        FROM situations
        WHERE att_alive = ? AND def_alive = ?
        """
        
        # We use exact match for map name if possible, or fall back to ILIKE
        params = [f"{map_name}", attackers_alive, defenders_alive]
        rows = db.query(sql, params)
        
        if not rows or rows[0][0] == 0:
            return {
                "probability": None,
                "sample_size": 0,
                "message": f"No historical data for {attackers_alive}v{defenders_alive} on {map_name}."
            }
            
        sample_size = int(rows[0][0])
        prob = round(float(rows[0][1]), 3)
        
        # Strategic Reasoning logic
        reasoning = ""
        if attackers_alive > defenders_alive:
            reasoning = f"Man disadvantage ({attackers_alive}v{defenders_alive}) makes retaking statistically unfavorable. "
        elif defenders_alive > attackers_alive:
            reasoning = f"Man advantage ({attackers_alive}v{defenders_alive}) significantly favors the retake. "
        else:
            reasoning = f"Even man count ({attackers_alive}v{defenders_alive}) favors the post-plant holders (Attackers) due to time pressure. "

        if prob < 0.25:
            reasoning += "Recommend SAVING weapons to preserve economy for the next round."
        elif prob > 0.45:
            reasoning += "High success probability. Recommend a COORDINATED RETAKE."
        else:
            reasoning += "Marginal scenario. Base decision on available ultimate utility and armor state."

        return {
            "scenario": {
                "map": map_name,
                "attackers_alive": attackers_alive,
                "defenders_alive": defenders_alive,
                "type": "retake_prediction"
            },
            "prediction": {
                "win_probability": prob,
                "win_percentage": f"{prob * 100:.1f}%",
                "sample_size": sample_size,
                "confidence_score": min(1.0, sample_size / 100.0),
                "confidence_label": "High" if sample_size > 50 else "Moderate" if sample_size > 15 else "Low"
            },
            "strategic_reasoning": reasoning,
            "recommendation": "Save" if prob < 0.3 else "Retake"
        }


async def analyze_economy_impact(
    team_name: str,
    map_name: str,
    round_number: int,
    decision: str  # 'save' or 'force'
) -> Dict[str, Any]:
    """
    Analyze the impact of an economy decision (save vs force) on subsequent rounds.
    This helps answer 'Would it have been better to save?'.
    
    Simplified logic: Look at win rates of the NEXT 2 rounds given the current round outcome.
    """
    # This is a placeholder for the more complex economy logic.
    # For the Hackathon demo, we can simulate this with static probability factors 
    # or by querying the `agg_team_round_summary` for rounds with low equipment value.
    
    return {
        "analysis": "Data analysis pending implementation of full economy chain logic.",
        "heuristic": "Generally, saving 3 rifles increases next round win prob by ~40% vs a broken buy."
    }
