-- Player Daily Stats: Aggregated player performance per day
-- Grain: One row per (date, player_id)
-- Use case: Track player performance trends over time

CREATE TABLE IF NOT EXISTS agg_player_daily_stats (
    date DATE NOT NULL,
    player_id VARCHAR NOT NULL,
    player_name VARCHAR NOT NULL,
    PRIMARY KEY (date, player_id),

    -- Denormalized dimensions
    team_name VARCHAR,
    tournament_name VARCHAR,
    tournament_year INTEGER,

    -- Daily activity
    series_played INTEGER DEFAULT 0,
    series_won INTEGER DEFAULT 0,
    maps_played INTEGER DEFAULT 0,
    maps_won INTEGER DEFAULT 0,
    rounds_played INTEGER DEFAULT 0,
    rounds_won INTEGER DEFAULT 0,

    -- Aggregate metrics (sum across all games on this date)
    kills INTEGER DEFAULT 0,
    deaths INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    first_bloods INTEGER DEFAULT 0,
    first_deaths INTEGER DEFAULT 0,
    plants INTEGER DEFAULT 0,
    defuses INTEGER DEFAULT 0,
    damage_dealt FLOAT DEFAULT 0,
    damage_received FLOAT DEFAULT 0,

    -- Derived metrics
    kd_ratio FLOAT,  -- kills / deaths
    kda FLOAT,  -- (kills + assists) / deaths
    adr FLOAT,  -- average damage per round
    kpr FLOAT,  -- kills per round
    fk_percentage FLOAT,  -- first_bloods / rounds_played
    fd_percentage FLOAT,  -- first_deaths / rounds_played
    win_rate FLOAT,  -- series_won / series_played

    -- Agent diversity
    agents_played JSON,  -- Array of agents played on this date
    unique_agents_count INTEGER,

    -- Metadata
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_agg_player_daily_date ON agg_player_daily_stats(date);
CREATE INDEX IF NOT EXISTS idx_agg_player_daily_player ON agg_player_daily_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_agg_player_daily_player_name ON agg_player_daily_stats(player_name);
CREATE INDEX IF NOT EXISTS idx_agg_player_daily_team ON agg_player_daily_stats(team_name);
CREATE INDEX IF NOT EXISTS idx_agg_player_daily_year ON agg_player_daily_stats(tournament_year);
CREATE INDEX IF NOT EXISTS idx_agg_player_daily_player_date ON agg_player_daily_stats(player_id, date);
