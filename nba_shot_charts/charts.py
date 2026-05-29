import matplotlib.pyplot as plt

from .data.fetcher import get_assist_shots, get_player_id, get_shot_chart
from .plotter import hexbin_shot_chart, scatter_shot_chart


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
