"""DLT pipeline for MLB game data ingestion from MLB Stats API.

This module handles the extraction and loading of NY Yankees and NY Mets home game
schedules from the MLB Stats API into a DuckDB data warehouse.

Supported Teams:
- NY Yankees (team ID: 147) - Home games at Yankee Stadium
- NY Mets (team ID: 121) - Home games at Citi Field

Expected volume: ~55 home games for May-June 2024 period (25 Yankees + 30 Mets)
"""

import logging
import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import dlt
import requests

logger = logging.getLogger(__name__)

# Set dlt project directory to find .dlt config folder
os.environ["DLT_PROJECT_DIR"] = str(Path(__file__).parent)


@dlt.resource(
    name="mlb_games",
    write_disposition="merge",
    primary_key="game_id",
    table_name="mlb_games",
)
def mlb_games(
    start_date: str,
    end_date: str,
    team_ids: list[int] | None = None
) -> Iterator[dict[str, Any]]:
    """Extract MLB game schedules from MLB Stats API.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        team_ids: List of MLB team IDs (default: [147, 121] for Yankees and Mets)

    Yields:
        Dictionary records of MLB games with standardized fields.
        Only home games are included (away games filtered out).
    """
    if team_ids is None:
        team_ids = [147, 121]  # Yankees, Mets

    logger.info("Fetching MLB games for date range %s to %s for teams: %s",
                start_date, end_date, team_ids)

    total_games = 0

    for team_id in team_ids:
        logger.info("Fetching games for team ID %d", team_id)

        url = "https://statsapi.mlb.com/api/v1/schedule"
        params = {
            "sportId": 1,  # MLB
            "teamId": team_id,
            "startDate": start_date,
            "endDate": end_date,
            "hydrate": "team,venue"
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Process games
            home_games = 0
            for date_entry in data.get("dates", []):
                for game in date_entry.get("games", []):
                    # Filter: only include home games
                    home_team_id = game.get("teams", {}).get("home", {}).get("team", {}).get("id")

                    if home_team_id == team_id:
                        # This is a home game - yield it
                        yield {
                            "game_id": game.get("gamePk"),
                            "game_date": game.get("gameDate")[:10] if game.get("gameDate") else None,
                            "game_datetime": game.get("gameDate"),
                            "official_date": game.get("officialDate"),
                            "season": game.get("season"),
                            "game_type": game.get("gameType"),
                            "game_status": game.get("status", {}).get("detailedState"),
                            "home_team_id": home_team_id,
                            "home_team_name": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                            "away_team_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                            "away_team_name": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                            "venue_id": game.get("venue", {}).get("id"),
                            "venue_name": game.get("venue", {}).get("name"),
                            "_dlt_load_timestamp": datetime.now(),
                            "source_api": "mlb_stats_api"
                        }
                        home_games += 1
                        total_games += 1

            logger.info("Fetched %d home games for team ID %d", home_games, team_id)

        except requests.exceptions.RequestException as e:
            logger.error("MLB API request failed for team ID %d: %s", team_id, e)
            raise Exception(f"MLB Stats API unavailable for team {team_id}: {e}") from e

    logger.info("Pipeline summary: %d total games fetched", total_games)

    if total_games == 0:
        logger.warning("Warning: No games found for date range %s to %s", start_date, end_date)


def run_game_pipeline(
    start_date: str = "2024-05-01",
    end_date: str = "2024-06-30",
    destination: str = "duckdb",
    dataset_name: str = "raw_games",
) -> dict[str, Any]:
    """Run the MLB game data ingestion pipeline.

    Args:
        start_date: Start date for game data (YYYY-MM-DD)
        end_date: End date for game data (YYYY-MM-DD)
        destination: DLT destination name (default: "duckdb")
        dataset_name: Target dataset/schema name (default: "raw_games")

    Returns:
        Pipeline execution result information

    Examples:
        # Default: May-June 2024 for Yankees and Mets
        >>> run_game_pipeline()

        # Custom date range
        >>> run_game_pipeline("2024-07-01", "2024-08-31")
    """
    pipeline = dlt.pipeline(
        pipeline_name="game_ingestion",
        destination=destination,
        dataset_name=dataset_name,
    )

    # Run the pipeline
    load_info = pipeline.run(mlb_games(start_date, end_date))

    # Log summary
    logger.info("Pipeline completed: %s", load_info)
    logger.info("Loaded %s loads", load_info.loads_ids)

    return load_info


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Example usage: ingest games for May-June 2024 (matching bike data period)
    logger.info("Running MLB game pipeline for May-June 2024")
    result = run_game_pipeline("2024-05-01", "2024-06-30")
    logger.info("Game ingestion complete. Result: %s", result)
