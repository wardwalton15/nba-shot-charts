import datetime

import matplotlib.pyplot as plt

from .data.fetcher import (get_assist_shots, get_league_averages, get_player_id, get_shot_chart,
                           get_team_games, get_team_id, get_team_logo, get_team_ratings,
                           get_team_shot_chart)
from .plotter import (efficiency_diff_chart, freq_diff_chart, hexbin_shot_chart,
                      scatter_shot_chart, smooth_efficiency_diff_chart, smooth_freq_diff_chart,
                      team_tiers_chart, three_point_zone_chart)


def player_shot_chart(
    player_name: str,
    season: str,
    season_type: str = "Regular Season",
    chart_type: str = "scatter",
    color_by: str = "made",
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Generate a shot chart for a player.

    Args:
        player_name:  Full name, e.g. "Jalen Brunson"
        season:       NBA season string, e.g. "2025-26"
        season_type:  "Regular Season" or "Playoffs"
        chart_type:   "scatter" or "hexbin"
        color_by:     "made", "zone", or "distance" (scatter only)
        save_path:    File path to save PNG; if None, calls plt.show()

    Returns:
        (fig, ax) — caller can further customize before displaying
    """
    player_id = get_player_id(player_name)
    df = get_shot_chart(player_id, season, season_type)

    if df.empty:
        raise ValueError(f"No shot data found for {player_name} in {season} {season_type}")

    title = f"{player_name} | {season} {season_type}"

    if chart_type == "hexbin":
        fig, ax = hexbin_shot_chart(df, title, save_path=save_path)
    else:
        fig, ax = scatter_shot_chart(df, title, color_by=color_by, save_path=save_path)

    if save_path is None:
        plt.show()

    return fig, ax


def assist_shot_chart(
    assisting_player_name: str,
    season: str,
    season_type: str = "Regular Season",
    chart_type: str = "scatter",
    color_by: str = "made",
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Generate a shot chart for all shots assisted by a given player.

    Args:
        assisting_player_name:  Full name, e.g. "Nikola Jokic"
        season:                 NBA season string, e.g. "2025-26"
        season_type:            "Regular Season" or "Playoffs"
        chart_type:             "scatter" or "hexbin"
        color_by:               "made", "zone", or "distance" (scatter only)
        save_path:              File path to save PNG; if None, calls plt.show()

    Returns:
        (fig, ax)

    Note:
        First run for a full regular season fetches ~82 games of play-by-play
        and shot chart data (~3 minutes). Subsequent runs load from cache
        and complete in seconds.
    """
    player_id = get_player_id(assisting_player_name)
    df = get_assist_shots(player_id, season, season_type)

    if df.empty:
        raise ValueError(
            f"No assisted shot data found for {assisting_player_name} in {season} {season_type}"
        )

    title = f"Assisted by {assisting_player_name} | {season} {season_type}"

    if chart_type == "hexbin":
        fig, ax = hexbin_shot_chart(df, title, save_path=save_path)
    else:
        fig, ax = scatter_shot_chart(df, title, color_by=color_by, save_path=save_path)

    if save_path is None:
        plt.show()

    return fig, ax


def team_comparison_charts(
    team_name: str,
    season: str,
    freq_save_path: str | None = None,
    efficiency_save_path: str | None = None,
    chart_style: str = "hexbin",
    gridsize: int = 20,
    min_count: int = 5,
) -> tuple[tuple[plt.Figure, plt.Axes], tuple[plt.Figure, plt.Axes]]:
    """
    Generate both differential shot charts comparing Playoffs vs Regular Season for a team.

    Produces:
      1. Shot frequency differential — where did the team shoot more/less in the playoffs?
      2. Shot efficiency differential — where did pts/attempt increase/decrease in the playoffs?

    Args:
        team_name:            Full name, nickname, or partial match, e.g. "Knicks"
        season:               NBA season string e.g. "2025-26"
        freq_save_path:       Path to save frequency chart PNG; None calls plt.show()
        efficiency_save_path: Path to save efficiency chart PNG; None calls plt.show()
        gridsize:             Hexbin grid density (default 20)
        min_count:            Min combined shots for a bin to be visible (default 5)

    Returns:
        ((fig_freq, ax_freq), (fig_eff, ax_eff))
    """
    team_id = get_team_id(team_name)
    df_rs = get_team_shot_chart(team_id, season, "Regular Season")
    df_po = get_team_shot_chart(team_id, season, "Playoffs")

    if df_rs.empty:
        raise ValueError(f"No regular season shot data found for '{team_name}' in {season}")
    if df_po.empty:
        raise ValueError(f"No playoff shot data found for '{team_name}' in {season}")

    display_name = df_rs["TEAM_NAME"].iloc[0] if "TEAM_NAME" in df_rs.columns else team_name

    freq_title = f"{display_name} — Shot Frequency Differential\n{season} Playoffs vs. Regular Season"
    eff_title = f"{display_name} — Shot Efficiency Differential\n{season} Playoffs vs. Regular Season"

    if chart_style == "smooth":
        result_freq = smooth_freq_diff_chart(
            df_rs, df_po, freq_title,
            min_count=min_count, save_path=freq_save_path,
        )
        if freq_save_path is None:
            plt.show()
        result_eff = smooth_efficiency_diff_chart(
            df_rs, df_po, eff_title,
            min_count=min_count, save_path=efficiency_save_path,
        )
    else:
        result_freq = freq_diff_chart(
            df_rs, df_po, freq_title,
            gridsize=gridsize, min_count=min_count, save_path=freq_save_path,
        )
        if freq_save_path is None:
            plt.show()
        result_eff = efficiency_diff_chart(
            df_rs, df_po, eff_title,
            gridsize=gridsize, min_count=min_count, save_path=efficiency_save_path,
        )

    if efficiency_save_path is None:
        plt.show()

    return result_freq, result_eff


def team_three_point_chart(
    team_name: str,
    season: str,
    season_type: str = "Regular Season",
    compare_season: str | None = None,
    refresh: bool = False,
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Three-point shooting chart for a team: every 3PA as a make/miss, with each
    3PT zone shaded by FG% relative to league average for the same span.

    Args:
        team_name:       Full name, nickname, or partial match, e.g. "Knicks"
        season:          NBA season string, e.g. "2026-27"
        season_type:     "Regular Season" or "Playoffs"
        compare_season:  Optional prior season whose team 3P% is shown in the subtitle
        refresh:         Re-fetch instead of using the cache (use for an in-progress season)
        save_path:       File path to save PNG; if None, calls plt.show()

    Returns:
        (fig, ax)
    """
    team_id = get_team_id(team_name)
    df = get_team_shot_chart(team_id, season, season_type, refresh=refresh)
    if df.empty:
        raise ValueError(f"No shot data found for '{team_name}' in {season} {season_type}")
    league_avg = get_league_averages(season, season_type, refresh=refresh)
    games = get_team_games(team_id, season, season_type, refresh=refresh)

    display_name = df["TEAM_NAME"].iloc[0]
    threes = df[df["SHOT_TYPE"] == "3PT Field Goal"]
    fgm, fga = int(threes["SHOT_MADE_FLAG"].sum()), len(threes)
    lg3 = league_avg[league_avg["SHOT_ZONE_BASIC"].str.contains("3")]
    lg_pct = lg3["FGM"].sum() / lg3["FGA"].sum() * 100

    wins = int((games["WL"] == "W").sum())
    losses = int((games["WL"] == "L").sum())
    n_games = df["GAME_ID"].nunique()
    span = f"first {n_games} games" if season_type == "Regular Season" else season_type.lower()
    title = f"{display_name} 3-Point Shooting  |  {season} {span} ({wins}-{losses})"

    subtitle = f"{fgm}/{fga} from three ({fgm / fga * 100:.1f}%)   •   League avg {lg_pct:.1f}%"
    if compare_season:
        prev = get_team_shot_chart(team_id, compare_season, season_type)
        prev3 = prev[prev["SHOT_TYPE"] == "3PT Field Goal"]
        if not prev3.empty:
            subtitle += f"   •   {compare_season}: {prev3['SHOT_MADE_FLAG'].mean() * 100:.1f}%"

    game_lines = [
        f"{g.MATCHUP.split(' ', 1)[1]} {g.WL} {g.FG3M}/{g.FG3A}"
        for g in games.itertuples()
    ]
    by_player = (threes.groupby("PLAYER_NAME")["SHOT_MADE_FLAG"].agg(["sum", "count"])
                 .sort_values("count", ascending=False).head(7))
    player_lines = [f"{name.split(' ', 1)[-1]} {int(r['sum'])}/{int(r['count'])}"
                    for name, r in by_player.iterrows()]
    footer = "By game:  " + "   ".join(game_lines) + "\nBy player:  " + "   ".join(player_lines)

    fig, ax = three_point_zone_chart(df, league_avg, title, subtitle=subtitle,
                                     footer=footer, save_path=save_path)
    if save_path is None:
        plt.show()
    return fig, ax


def team_ratings_chart(
    season: str,
    season_type: str = "Regular Season",
    as_of: datetime.date | None = None,
    credit: str = "",
    refresh: bool = False,
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    League-wide tiers chart: every team's offensive vs. defensive rating, with
    diagonal bands grouping teams by net rating.

    Args:
        season:      NBA season string, e.g. "2026-27"
        season_type: "Regular Season" or "Playoffs"
        as_of:       Date for the "ENTERING ..." banner; defaults to today
        credit:      Byline in the bottom-right corner
        refresh:     Re-fetch instead of using the cache (use for an in-progress season)
        save_path:   File path to save PNG; if None, calls plt.show()

    Returns:
        (fig, ax)
    """
    df = get_team_ratings(season, season_type, refresh=refresh)
    logos = {abbr: get_team_logo(abbr) for abbr in df["abbreviation"]}

    # Possession-weighted, so it's the true league points per 100
    league_avg = (df["OFF_RATING"] * df["POSS"]).sum() / df["POSS"].sum()

    as_of = as_of or datetime.date.today()
    tag = f"ENTERING {as_of.strftime('%b').upper()} {as_of.day}"
    gp_lo, gp_hi = int(df["GP"].min()), int(df["GP"].max())
    games = f"{gp_lo}" if gp_lo == gp_hi else f"{gp_lo}–{gp_hi}"
    note = (f"Points scored / allowed per 100 possessions, {season} {season_type.lower()}"
            f" ({games} games per team).\nNet rating = offensive rating − defensive rating.")

    fig, ax = team_tiers_chart(df, logos, league_avg, tag, note=note, credit=credit,
                               save_path=save_path)
    if save_path is None:
        plt.show()
    return fig, ax
