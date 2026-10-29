import re
import time
import unicodedata

import numpy as np
import pandas as pd
import requests
from nba_api.stats.endpoints import (
    CommonPlayerInfo,
    LeagueDashTeamStats,
    LeagueGameFinder,
    PlayByPlayV3,
    ShotChartDetail,
    SynergyPlayTypes,
)
from nba_api.stats.static import players, teams

from .cache import IMG_DIR, cache_path, load_from_cache, save_to_cache

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
    refresh: bool = False,
) -> pd.DataFrame:
    """Set refresh=True for an in-progress season so new games aren't missed."""
    key = f"shots_team_{team_id}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
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


def get_league_averages(
    season: str,
    season_type: str,
    refresh: bool = False,
) -> pd.DataFrame:
    """League-wide FGA/FGM by shot zone (the LeagueAverages frame of ShotChartDetail)."""
    key = f"league_avg_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
    if cached is not None:
        return cached

    result = _sleep_and_fetch(
        ShotChartDetail,
        player_id=0,
        team_id=0,
        season_nullable=season,
        season_type_all_star=season_type,
        context_measure_simple="FGA",
    )
    df = result.get_data_frames()[1]
    save_to_cache(df, path)
    return df


def get_team_games(
    team_id: int,
    season: str,
    season_type: str,
    refresh: bool = False,
) -> pd.DataFrame:
    """One row per game for the team (GAME_ID, GAME_DATE, MATCHUP, WL, PTS, FG3M, FG3A, ...)."""
    key = f"games_team_{team_id}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
    if cached is not None:
        return cached

    result = _sleep_and_fetch(
        LeagueGameFinder,
        team_id_nullable=team_id,
        season_nullable=season,
        season_type_nullable=season_type,
        league_id_nullable="00",
    )
    df = result.get_data_frames()[0].sort_values("GAME_DATE").reset_index(drop=True)
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


def _get_game_ids(season: str, season_type: str, refresh: bool = False) -> list[str]:
    """Set refresh=True for an in-progress season so new games aren't missed."""
    key = f"game_ids_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
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


def get_play_type_stats(
    play_type: str,
    season: str,
    season_type: str,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Synergy offensive play-type totals, one row per player.

    play_type is a Synergy key, e.g. "PRBallHandler", "PRRollman", "Isolation".
    Synergy credits a possession to the player who *finishes* it (shot, shooting
    foul or turnover) — a P&R where the ballhandler passes out isn't counted here.
    """
    key = f"synergy_{play_type}_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
    if cached is not None:
        return cached

    result = _sleep_and_fetch(
        SynergyPlayTypes,
        league_id="00",
        per_mode_simple="Totals",
        play_type_nullable=play_type,
        player_or_team_abbreviation="P",
        season_type_all_star=season_type,
        season=season,
        type_grouping_nullable="offensive",
    )
    df = result.get_data_frames()[0]
    save_to_cache(df, path)
    return df


def _fold(name: str) -> str:
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().strip()


def _resolve_assister(name: str, roster: pd.DataFrame) -> int | None:
    """
    Match the PBP assist name to a personId on that team's game roster.
    Handles "Suggs", "Doncic" vs "Dončić", "F. Wagner", and "Jal. Williams".
    """
    target = _fold(name)
    for col in ("playerName", "playerNameI"):
        hits = roster.loc[roster[col].map(_fold) == target, "personId"].unique()
        if len(hits) == 1:
            return int(hits[0])

    # "Jal. Williams": last-name candidates whose first name starts with the prefix
    prefix, _, last = target.partition(". ")
    if last:
        candidates = roster.loc[roster["playerName"].map(_fold) == last, "personId"].unique()
        hits = []
        for pid in candidates:
            info = players.find_player_by_id(int(pid))
            if info and _fold(info["first_name"]).startswith(prefix):
                hits.append(int(pid))
        if len(hits) == 1:
            return hits[0]
    return None


def get_assist_pairs(
    season: str,
    season_type: str,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    One row per assisted field goal: GAME_ID, TEAM_ID, SCORER_ID, ASSISTER_ID, SHOT_VALUE.

    PlayByPlayV3 only names the assister by last name inside the description
    ("... (Suggs 2 AST)"), so it's resolved against the players who logged an
    action for the same team in the same game. Unresolvable rows keep ASSISTER_ID = NA.
    Set refresh=True for an in-progress season so new games are picked up
    (per-game PBP stays cached either way).
    """
    key = f"assist_pairs_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
    if cached is not None:
        return cached

    ast_pattern = re.compile(r"\(([^()]+?)\s+\d+\s+AST\)")
    game_ids = _get_game_ids(season, season_type, refresh=refresh)
    print(f"Scanning {len(game_ids)} games for assists...")

    rows = []
    for game_id in game_ids:
        pbp = _get_game_pbp(game_id)
        players_in_game = pbp.loc[pbp["personId"] > 0, ["teamId", "personId", "playerName", "playerNameI"]]
        made = pbp[(pbp["shotResult"] == "Made") & pbp["description"].str.contains("AST", na=False)]
        for _, shot in made.iterrows():
            m = ast_pattern.search(shot["description"])
            if not m:
                continue
            roster = players_in_game[players_in_game["teamId"] == shot["teamId"]]
            rows.append({
                "GAME_ID": game_id,
                "TEAM_ID": int(shot["teamId"]),
                "SCORER_ID": int(shot["personId"]),
                "ASSISTER_ID": _resolve_assister(m.group(1).strip(), roster),
                "SHOT_VALUE": int(shot["shotValue"]),
            })

    df = pd.DataFrame(rows).astype({"ASSISTER_ID": "Int64"})
    save_to_cache(df, path)
    return df


def get_team_ratings(
    season: str,
    season_type: str,
    refresh: bool = False,
) -> pd.DataFrame:
    """Advanced team stats, one row per team (OFF_RATING, DEF_RATING, NET_RATING, POSS, ...)."""
    key = f"team_ratings_{season}_{season_type.replace(' ', '_')}"
    path = cache_path(key)
    cached = None if refresh else load_from_cache(path)
    if cached is not None:
        return cached

    result = _sleep_and_fetch(
        LeagueDashTeamStats,
        season=season,
        season_type_all_star=season_type,
        measure_type_detailed_defense="Advanced",
    )
    df = result.get_data_frames()[0]
    df = df.merge(pd.DataFrame(teams.get_teams())[["id", "abbreviation"]],
                  left_on="TEAM_ID", right_on="id").drop(columns="id")
    save_to_cache(df, path)
    return df


# ESPN's logo slugs where they differ from the NBA abbreviation
_ESPN_ABBR = {"GSW": "gs", "NYK": "ny", "NOP": "no", "SAS": "sa", "UTA": "utah", "WAS": "wsh"}


def get_team_logo(abbreviation: str) -> np.ndarray:
    """
    Team logo as an RGBA array, trimmed to its visible pixels.

    Uses ESPN's 500px PNGs — the NBA CDN only serves SVG, which matplotlib can't draw.
    """
    from PIL import Image

    slug = _ESPN_ABBR.get(abbreviation, abbreviation.lower())
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    path = IMG_DIR / f"espn_logo_{slug}.png"
    if not path.exists():
        resp = requests.get(f"https://a.espncdn.com/i/teamlogos/nba/500/{slug}.png", timeout=20)
        resp.raise_for_status()
        path.write_bytes(resp.content)

    img = Image.open(path).convert("RGBA")
    return np.asarray(img.crop(img.getbbox()))
