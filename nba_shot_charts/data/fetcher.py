import re
import time

import pandas as pd
from nba_api.stats.endpoints import (
    CommonPlayerInfo,
    LeagueGameFinder,
    PlayByPlayV3,
    ShotChartDetail,
)
from nba_api.stats.static import players, teams

from .cache import cache_path, load_from_cache, save_to_cache

_SLEEP = 0.6  # seconds between live API calls


def _sleep_and_fetch(fn, *args, **kwargs):
    time.sleep(_SLEEP)
    return fn(*args, **kwargs)


def get_player_id(name: str) -> int:
    matches = players.find_players_by_full_name(name)
    if not matches:
        # Case-insensitive substring fallback
        lower = name.lower()
        matches = [p for p in players.get_players() if lower in p["full_name"].lower()]
    if not matches:
        raise ValueError(f"No NBA player found matching '{name}'")
    if len(matches) > 1:
        names = [m["full_name"] for m in matches]
        raise ValueError(f"Ambiguous player name '{name}', matches: {names}")
    return matches[0]["id"]


def get_team_id(name: str) -> int:
    matches = teams.find_teams_by_full_name(name)
    if not matches:
        lower = name.lower()
        matches = [
            t for t in teams.get_teams()
            if lower in t["full_name"].lower()
            or lower in t["nickname"].lower()
            or lower in t["abbreviation"].lower()
        ]
    if not matches:
        raise ValueError(f"No NBA team found matching '{name}'")
    if len(matches) > 1:
        names = [m["full_name"] for m in matches]
        raise ValueError(f"Ambiguous team name '{name}', matches: {names}")
    return matches[0]["id"]


def get_team_shot_chart(
    team_id: int,
    season: str,
    season_type: str,
) -> pd.DataFrame:
    key = f"shots_team_{team_id}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached

    result = _sleep_and_fetch(
        ShotChartDetail,
        player_id=0,
        team_id=team_id,
        season_nullable=season,
        season_type_all_star=season_type,
        context_measure_simple="FGA",
    )
    df = result.get_data_frames()[0]
    save_to_cache(df, path)
    return df


def get_shot_chart(
    player_id: int,
    season: str,
    season_type: str,
) -> pd.DataFrame:
    key = f"shots_player_{player_id}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached

    result = _sleep_and_fetch(
        ShotChartDetail,
        player_id=player_id,
        team_id=0,
        season_nullable=season,
        season_type_all_star=season_type,
        context_measure_simple="FGA",
    )
    df = result.get_data_frames()[0]
    save_to_cache(df, path)
    return df


def _get_game_pbp(game_id: str) -> pd.DataFrame:
    key = f"pbp_{game_id}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached

    print(f"  Fetching PBP for game {game_id}...")
    result = _sleep_and_fetch(PlayByPlayV3, game_id=game_id)
    df = result.play_by_play.get_data_frame()
    save_to_cache(df, path)
    return df


def _get_game_shots(game_id: str) -> pd.DataFrame:
    key = f"shots_game_{game_id}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached

    print(f"  Fetching shots for game {game_id}...")
    result = _sleep_and_fetch(
        ShotChartDetail,
        player_id=0,
        team_id=0,
        game_id_nullable=game_id,
        context_measure_simple="FGA",
    )
    df = result.get_data_frames()[0]
    save_to_cache(df, path)
    return df


def _get_game_ids(season: str, season_type: str) -> list[str]:
    key = f"game_ids_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached["GAME_ID"].tolist()

    print(f"Fetching game list for {season} {season_type}...")
    result = _sleep_and_fetch(
        LeagueGameFinder,
        season_nullable=season,
        season_type_nullable=season_type,
        league_id_nullable="00",
    )
    df = result.get_data_frames()[0]
    # Each game appears twice (once per team), deduplicate
    game_ids = df["GAME_ID"].drop_duplicates().tolist()
    save_to_cache(pd.DataFrame({"GAME_ID": game_ids}), path)
    return game_ids


def _get_player_team_id(player_id: int) -> int:
    """Look up the player's current team ID via CommonPlayerInfo."""
    result = _sleep_and_fetch(CommonPlayerInfo, player_id=player_id)
    info = result.get_data_frames()[0]
    return int(info["TEAM_ID"].iloc[0])


def get_assist_shots(
    assisting_player_id: int,
    season: str,
    season_type: str,
) -> pd.DataFrame:
    """
    Return all shot chart rows for shots assisted by assisting_player_id.

    Strategy:
      1. Resolve player last name and current team.
      2. Get the team's full season shot chart (works; per-game endpoint is broken).
      3. Scan PBP for all games, extract (game_id, actionNumber) pairs where
         description contains "(LastName N AST)".
      4. Join team shot chart on (GAME_ID, GAME_EVENT_ID).
    """
    key = f"assists_{assisting_player_id}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached

    player_info = players.find_player_by_id(assisting_player_id)
    if not player_info:
        raise ValueError(f"No player found for ID {assisting_player_id}")
    last_name = player_info["last_name"]

    assist_pattern = re.compile(
        rf"\({re.escape(last_name)}\s+\d+\s+AST\)", re.IGNORECASE
    )

    # Full-season team shot chart — per-game endpoint unreliable for recent games
    team_id = _get_player_team_id(assisting_player_id)
    all_shots = get_team_shot_chart(team_id, season, season_type)
    if all_shots.empty:
        return pd.DataFrame()

    game_ids = _get_game_ids(season, season_type)
    # Restrict to games the team actually played
    team_game_ids = set(all_shots["GAME_ID"].unique())
    game_ids = [g for g in game_ids if g in team_game_ids]

    print(f"Scanning {len(game_ids)} games for assists by {last_name}...")

    # Collect (game_id, action_number) pairs from PBP
    assist_lookup: dict[str, list[int]] = {}
    for game_id in game_ids:
        pbp = _get_game_pbp(game_id)
        if "description" not in pbp.columns:
            continue
        action_nums = pbp.loc[
            pbp["description"].astype(str).str.contains(
                assist_pattern.pattern, regex=True, case=False, na=False
            ),
            "actionNumber",
        ].tolist()
        if action_nums:
            assist_lookup[game_id] = action_nums

    if not assist_lookup:
        return pd.DataFrame()

    # Join against the team shot chart
    masks = [
        (all_shots["GAME_ID"] == gid) & (all_shots["GAME_EVENT_ID"].isin(events))
        for gid, events in assist_lookup.items()
    ]
    combined_mask = masks[0]
    for m in masks[1:]:
        combined_mask = combined_mask | m

    df = all_shots[combined_mask].copy()
    df["ASSIST_PLAYER_ID"] = assisting_player_id
    save_to_cache(df, path)
    return df
