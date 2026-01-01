-- Series metadata table
CREATE TABLE IF NOT EXISTS series (
    series_id VARCHAR PRIMARY KEY,
    tournament_id VARCHAR,
    tournament_name VARCHAR,
    tournament_year INTEGER,
    tournament_region VARCHAR,
    team1_name VARCHAR,
    team2_name VARCHAR,
    winning_team_name VARCHAR,
    start_time TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_series_tournament ON series(tournament_id);
CREATE INDEX IF NOT EXISTS idx_series_tournament_name ON series(tournament_name);
CREATE INDEX IF NOT EXISTS idx_series_year ON series(tournament_year);
CREATE INDEX IF NOT EXISTS idx_series_start_time ON series(start_time);
