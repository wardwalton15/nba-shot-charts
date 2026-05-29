import time

import pandas as pd
from nba_api.stats.endpoints import (
    LeagueGameFinder,
    PlayByPlayV2,
    ShotChartDetail,
)
from nba_api.stats.static import players

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
    result = _sleep_and_fetch(PlayByPlayV2, game_id=game_id)
    df = result.get_data_frames()[0]
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


def get_assist_shots(
    assisting_player_id: int,
    season: str,
    season_type: str,
) -> pd.DataFrame:
    """
    Return all shot chart rows for shots assisted by assisting_player_id.

    Join logic: PlayByPlayV2.EVENTNUM == ShotChartDetail.GAME_EVENT_ID
    within the same GAME_ID. PLAYER3_ID in PBP is always the assisting player.
    """
    key = f"assists_{assisting_player_id}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = load_from_cache(path)
    if cached is not None:
        return cached

    game_ids = _get_game_ids(season, season_type)
    print(f"Scanning {len(game_ids)} games for assists by player {assisting_player_id}...")

    results = []
    for game_id in game_ids:
        pbp = _get_game_pbp(game_id)

        # PLAYER3_ID is the assisting player; filter to our target
        assist_events = pbp[
            pbp["PLAYER3_ID"].astype(str) == str(assisting_player_id)
        ]["EVENTNUM"].tolist()

        if not assist_events:
            continue

        shots = _get_game_shots(game_id)
        assisted = shots[shots["GAME_EVENT_ID"].isin(assist_events)].copy()
        assisted["ASSIST_PLAYER_ID"] = assisting_player_id
        results.append(assisted)

    if not results:
        return pd.DataFrame()

    df = pd.concat(results, ignore_index=True)
    save_to_cache(df, path)
    return df
