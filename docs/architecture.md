# Assistant Coach Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ASSISTANT COACH ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │             │    │                 │    │                             │ │
│  │  DATA MODEL │───▶│   MCP TOOLS     │───▶│      LLM LAYER              │ │
│  │   (Brain)   │    │   (Bridge)      │    │  (Insight Generator)        │ │
│  │             │    │                 │    │                             │ │
│  └─────────────┘    └─────────────────┘    └─────────────────────────────┘ │
│        │                    │                          │                    │
│        ▼                    ▼                          ▼                    │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────────────────┐ │
│  │ • DuckDB    │    │ • query_sql     │    │ • Claude (Desktop/API)     │ │
│  │ • GRID API  │    │ • match_report  │    │ • Gemini CLI               │ │
│  │ • Agg Tables│    │ • player_report │    │                             │ │
│  │ • Events    │    │ • scouting      │    │ Generates:                  │ │
│  │             │    │ • patterns      │    │ • Coaching insights         │ │
│  │             │    │                 │    │ • Recommendations           │ │
│  │             │    │ Returns:        │    │ • Natural language          │ │
│  │             │    │ • Structured    │    │ • VOD review priorities     │ │
│  │             │    │   JSON          │    │ • Action plans              │ │
│  │             │    │ • num/denom     │    │                             │ │
│  │             │    │ • No insights   │    │                             │ │
│  └─────────────┘    └─────────────────┘    └─────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### Layer 1: Data Model (Brain)

**Purpose:** Store and organize esports match data.

**Technology:**
- DuckDB (local / columnar queries)
- GRID API (data source)

**Key tables:**
`series`, `games`, `rounds`, `base_events`, `agg_player_round_stats`,
`agg_player_game_stats`, `agg_team_round_stats`, `agg_team_game_stats`

**Design decisions:**
- Pre-aggregated tables for fast queries
- Numerator/denominator columns for rates (no precomputed %)
- Timing preserved for tempo analysis
- Boolean flags for filtering (`is_clutch`, `is_opening_death`, etc.)

### Layer 2: MCP Tools (Bridge)

**Purpose:** Structured data retrieval for LLM consumption.

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

**Data-only output example:**
```json
{
  "kast_impact": {
    "deaths_without_kast": 314,
    "rounds_lost_when_no_kast": 251,
    "loss_rate_when_no_kast": 79.9
  }
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

```
User Request
   ↓
LLM selects MCP tools
   ↓
MCP returns JSON metrics
   ↓
LLM generates insights
```

