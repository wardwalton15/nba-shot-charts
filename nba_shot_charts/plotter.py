import matplotlib.pyplot as plt
import pandas as pd

from .court import draw_court

# Zone color mapping for color_by='zone'
_ZONE_COLORS = {
    "Restricted Area": "#1f77b4",
    "In The Paint (Non-RA)": "#aec7e8",
    "Mid-Range": "#ff7f0e",
    "Left Corner 3": "#2ca02c",
    "Right Corner 3": "#2ca02c",
    "Above the Break 3": "#9467bd",
    "Backcourt": "#7f7f7f",
}


def _build_color_series(df: pd.DataFrame, color_by: str) -> tuple[list, list, dict]:
    """Return (made_colors, missed_colors, legend_handles) for the given color_by mode."""
    if color_by == "made":
        return "#2ecc71", "#e74c3c", {
            "Made": {"color": "#2ecc71", "marker": "o"},
            "Missed": {"color": "#e74c3c", "marker": "x"},
        }
    if color_by == "zone":
        made_colors = df.loc[df["SHOT_MADE_FLAG"] == 1, "SHOT_ZONE_BASIC"].map(
            lambda z: _ZONE_COLORS.get(z, "#999999")
        )
        missed_colors = df.loc[df["SHOT_MADE_FLAG"] == 0, "SHOT_ZONE_BASIC"].map(
            lambda z: _ZONE_COLORS.get(z, "#999999")
        )
        legend = {zone: {"color": color, "marker": "o"} for zone, color in _ZONE_COLORS.items()}
        return made_colors, missed_colors, legend
    # distance: continuous colormap, ignore made/missed split for coloring
    return None, None, {}


def scatter_shot_chart(
    df: pd.DataFrame,
    title: str,
    color_by: str = "made",
    fig_size: tuple = (10, 9),
    alpha: float = 0.6,
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=fig_size)
    draw_court(ax)

    made = df[df["SHOT_MADE_FLAG"] == 1]
    missed = df[df["SHOT_MADE_FLAG"] == 0]

    if color_by == "made":
        ax.scatter(made["LOC_X"], made["LOC_Y"], c="#2ecc71", marker="o",
                   s=30, alpha=alpha, linewidths=0.5, edgecolors="black", zorder=3, label="Made")
        ax.scatter(missed["LOC_X"], missed["LOC_Y"], c="#e74c3c", marker="x",
                   s=30, alpha=alpha, linewidths=1.0, zorder=3, label="Missed")
        ax.legend(loc="upper right", fontsize=9, framealpha=0.8)

    elif color_by == "zone":
        for zone, color in _ZONE_COLORS.items():
            z_made = made[made["SHOT_ZONE_BASIC"] == zone]
            z_missed = missed[missed["SHOT_ZONE_BASIC"] == zone]
            if not z_made.empty:
                ax.scatter(z_made["LOC_X"], z_made["LOC_Y"], c=color, marker="o",
                           s=30, alpha=alpha, edgecolors="black", linewidths=0.5, zorder=3, label=zone)
            if not z_missed.empty:
                ax.scatter(z_missed["LOC_X"], z_missed["LOC_Y"], c=color, marker="x",
                           s=30, alpha=alpha, linewidths=1.0, zorder=3)
        ax.legend(loc="upper right", fontsize=8, framealpha=0.8)

    elif color_by == "distance":
        sc = ax.scatter(df["LOC_X"], df["LOC_Y"], c=df["SHOT_DISTANCE"],
                        cmap="plasma", s=30, alpha=alpha, zorder=3)
        plt.colorbar(sc, ax=ax, label="Distance (ft)", shrink=0.6)

    n_made = int(made.shape[0])
    n_total = int(df.shape[0])
    pct = f"{n_made / n_total * 100:.1f}%" if n_total > 0 else "—"
    ax.set_title(f"{title}\n{n_made}/{n_total} FGM ({pct})", fontsize=13, fontweight="bold", pad=10)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig, ax


def hexbin_shot_chart(
    df: pd.DataFrame,
    title: str,
    cmap: str = "YlOrRd",
    gridsize: int = 20,
    fig_size: tuple = (10, 9),
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=fig_size)
    draw_court(ax)

    hb = ax.hexbin(
        df["LOC_X"], df["LOC_Y"],
        gridsize=gridsize,
        cmap=cmap,
        extent=(-250, 250, -47.5, 422.5),
        mincnt=1,
        alpha=0.8,
        zorder=3,
    )
    plt.colorbar(hb, ax=ax, label="Shot attempts", shrink=0.6)

    ax.set_title(f"{title}\n{len(df)} FGA", fontsize=13, fontweight="bold", pad=10)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig, ax
