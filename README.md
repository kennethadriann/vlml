# VLML - Valorant Analytics MCP Server

VLML provides **data-only analytics** for Valorant. It exposes an MCP server backed by DuckDB and aggregated metrics so an LLM (Claude/Gemini/etc.) can generate coaching insights.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

Download raw events and build the database:

```bash
python database/scripts/ingestion/download_raw_events.py --year 2025
python database/scripts/orchestration/run_pipeline.py --year 2025
```

Run the MCP server:

```bash
vlml
```

Or:

```bash
.venv/bin/python -m vlml.server
```

## Tools (Data-Only)

Insights tools:
- `match_analysis_report`
- `player_profile_report`
- `scouting_report`
- `pattern_detection_report`

Database tools:
- `query_sql`
- `get_database_info`

See `docs/tools.md` for input/output details.

## Documentation

- Setup: `docs/setup.md`
- Tools: `docs/tools.md`
- Architecture: `docs/architecture.md`
- Database pipeline: `database/README.md`
- Data model: `database/DATA_MODEL.md`
- Report standard: `insights_reference.md`

## Notes

- No prebuilt database is shipped. Use the pipeline to build `data/vlml_events.duckdb`.
- All reports return metrics and evidence only. LLMs should generate insights and recommendations.
