import matplotlib.pyplot as plt

from .data.fetcher import get_assist_shots, get_player_id, get_shot_chart, get_team_id, get_team_shot_chart
from .plotter import (efficiency_diff_chart, freq_diff_chart, hexbin_shot_chart,
                      scatter_shot_chart, smooth_efficiency_diff_chart, smooth_freq_diff_chart)


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
