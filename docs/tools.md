# Tools Reference

These tools return **data-only metrics**. LLMs should generate narratives and recommendations.

## Insights Tools

### `match_analysis_report`
**Input**
```
{ "series_id": "string", "team_name"?: "string", "map_name"?: "string" }
```

**Output**
- `report_type`, `series_id`, `team_name`
- `scope` (maps, rounds, confidence)
- `key_metrics` (team + opponent)
- `round_timeline` (per round opener, winner, highlight, flag)
- `notes`

### `player_profile_report`
**Input**
```
{ "player_name": "string", "series_ids"?: ["..."], "last_n_series"?: 5, "map_name"?: "string", "agent_name"?: "string" }
```

**Output**
- `report_type`, `player_name`
- `scope` (series, rounds, confidence)
- `key_metrics`
- `notes`

### `scouting_report`
**Input**
```
{ "team_name": "string", "series_ids"?: ["..."], "last_n_series"?: 5, "map_name"?: "string" }
```

**Output**
- `report_type`, `team_name`
- `scope` (series, rounds, confidence)
- `key_metrics`
- `notes`

### `pattern_detection_report`
**Input**
```
{ "team_name"?: "string", "player_name"?: "string", "tournament_name"?: "string", "series_ids"?: ["..."], "min_rounds"?: 200 }
```

**Output**
- `report_type`, `subject`
- `scope` (series, rounds, confidence)
- `summary` (facts only)
- `key_metrics`
- `notes`

## Database Tools

### `query_sql`
Execute a `SELECT` query on DuckDB.

### `get_database_info`
Returns row counts, recent series, and table list.

## Confidence Labels

- **strong**: rounds >= 100
- **moderate**: 50–99
- **weak**: 20–49
- **insufficient**: < 20

