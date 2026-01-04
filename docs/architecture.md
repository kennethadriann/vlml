# VLML Architecture

## System Overview

Modeling layer → MCP tools → LLM layer

- **Modeling layer (Product)**: DuckDB OLAP tables built from raw GRID JSON.
- **MCP tools (Bridge)**: Data-only endpoints like `match_analysis_report` and `query_sql`.
- **LLM layer (Insights)**: Claude/Gemini converts metrics into coaching narratives.

## Layer Responsibilities

### Layer 1: Data Model (Product)

**Purpose:** Convert raw GRID JSON into a consistent OLAP model for analytics.

**Technology:**
- DuckDB (local / columnar queries)
- GRID JSON exports (raw source data)

**Key tables:**
`series`, `games`, `rounds`, `base_events`, `agg_player_round_stats`,
`agg_player_game_stats`, `agg_team_round_stats`, `agg_team_game_stats`

**Design decisions:**
- Pre-aggregated tables for fast queries
- Numerator/denominator columns for rates (no precomputed %)
- Timing preserved for tempo analysis
- Boolean flags for filtering (`is_clutch`, `is_opening_death`, etc.)

### Layer 2: MCP Tools (Bridge)

**Purpose:** Structured data delivery for LLM consumption.

**Design principles:**
1. Data only (no insights in MCP output)
2. Numerator/denominator format for rates
3. Consistent schemas for LLM parsing

**Tools:**
- `query_sql`
- `match_analysis_report`
- `player_profile_report`
- `scouting_report`
- `pattern_detection_report`
- `get_database_info`

**Data-only output example (match_analysis_report):**
```json
{
  "report_type": "match_analysis",
  "version": "2.0",
  "series_id": "2843069",
  "team_name": "Cloud9",
  "scope": {
    "maps": ["haven", "lotus", "corrode"],
    "rounds": 61,
    "confidence": "moderate"
  },
  "kast_impact_analysis": [
    {
      "player_name": "mitch",
      "team_name": "Cloud9",
      "deaths_without_kast": 21,
      "rounds_lost_when_no_kast": 19,
      "loss_rate_when_no_kast": 90.5
    }
  ]
}
```

### Layer 3: LLM Layer (Insight Generator)

**Purpose:** Convert structured metrics into coaching insights.

**Supported LLMs:**
- Claude (Desktop/API)
- Gemini CLI

**LLM responsibilities:**
1. Interpret metrics
2. Identify patterns
3. Generate recommendations
4. Prioritize VOD review

## Data Flow

1. User request comes in.
2. LLM selects MCP tools.
3. MCP returns structured JSON metrics.
4. LLM generates insights and recommendations.
