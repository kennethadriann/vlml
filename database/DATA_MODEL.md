# VLML Data Model

This document describes table grains and relationships. Use `database/metadata/column_definitions.yaml` for column-level details.

## Core Relationships

```
series (series_id)
  └─ games (game_id, series_id)
       └─ rounds (round_id, game_id)
            └─ base_events (event_id, round_id)
```

## Reference Tables

- `agent_roles`: one row per agent, role mapping
- `weapon_types`: one row per weapon, type/cost mapping
- `map_zones`: map bounding boxes for site/default zones
- `ability_types`: ability name/type mapping (seed JSON)

## Aggregation Tables

### Player Round (`agg_player_round_stats`)
**Grain:** `(round_id, player_id)`  
**Use cases:** opening duels, trades, clutch flags, utility impact, weapon usage.

### Player Game (`agg_player_game_stats`)
**Grain:** `(game_id, player_id)`  
**Use cases:** per-map performance, K/D, ADR, KAST, opening duel and trade rollups.

### Player Series (`agg_player_series_stats`)
**Grain:** `(series_id, player_id)`  
**Use cases:** multi-map summaries, consistency over a match.

### Player Daily (`agg_player_daily_stats`)
**Grain:** `(date, player_id)`  
**Use cases:** trend analysis over time.

### Team Round (`agg_team_round_stats`)
**Grain:** `(round_id, team_name)`  
**Use cases:** round-by-round results, entry conversion, trades, tempo, economy.

### Team Game (`agg_team_game_stats`)
**Grain:** `(game_id, team_name)`  
**Use cases:** team map performance, composition, opening duels, post-plant stats.

### Tournament (`agg_tournament_stats`)
**Grain:** `(tournament_id, entity_type, entity_id)`  
**Use cases:** tournament-level rollups for teams and players.
