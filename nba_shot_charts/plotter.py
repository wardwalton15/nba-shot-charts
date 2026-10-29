import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

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


_EXTENT = (-250, 250, -47.5, 422.5)


def _measure_hexbin_grid(x_rs, y_rs, x_po, y_po, gridsize: int):
    """
    Run hexbin on both datasets with mincnt=0 on a shared hidden figure.
    Returns (rs_counts, po_counts) arrays guaranteed to be the same length
    because the grid is determined solely by extent + gridsize.
    """
    fig_tmp, ax_tmp = plt.subplots()
    hb_rs = ax_tmp.hexbin(x_rs, y_rs, gridsize=gridsize, extent=_EXTENT, mincnt=0)
    rs_counts = hb_rs.get_array().copy()
    hb_po = ax_tmp.hexbin(x_po, y_po, gridsize=gridsize, extent=_EXTENT, mincnt=0)
    po_counts = hb_po.get_array().copy()
    plt.close(fig_tmp)
    assert len(rs_counts) == len(po_counts), "Hexbin grid mismatch — same gridsize/extent required"
    return rs_counts, po_counts


def _measure_hexbin_pts(x_rs, y_rs, pts_rs, x_po, y_po, pts_po, gridsize: int):
    """
    Run four hexbin passes to get pts_sum and count per bin for RS and PO.
    Returns (rs_pts_sum, rs_count, po_pts_sum, po_count).
    """
    fig_tmp, ax_tmp = plt.subplots()
    hb_rs_pts = ax_tmp.hexbin(x_rs, y_rs, C=pts_rs, reduce_C_function=np.sum,
                               gridsize=gridsize, extent=_EXTENT, mincnt=0)
    hb_rs_cnt = ax_tmp.hexbin(x_rs, y_rs, gridsize=gridsize, extent=_EXTENT, mincnt=0)
    hb_po_pts = ax_tmp.hexbin(x_po, y_po, C=pts_po, reduce_C_function=np.sum,
                               gridsize=gridsize, extent=_EXTENT, mincnt=0)
    hb_po_cnt = ax_tmp.hexbin(x_po, y_po, gridsize=gridsize, extent=_EXTENT, mincnt=0)
    rs_pts_sum = hb_rs_pts.get_array().copy()
    rs_count = hb_rs_cnt.get_array().copy()
    po_pts_sum = hb_po_pts.get_array().copy()
    po_count = hb_po_cnt.get_array().copy()
    plt.close(fig_tmp)
    return rs_pts_sum, rs_count, po_pts_sum, po_count


def _apply_diff_to_hexbin(ax, x_po, y_po, diff: np.ndarray, gridsize: int,
                           cmap_name: str, alpha: float):
    """Draw a hexbin on ax with the precomputed diff array applied."""
    cmap = plt.get_cmap(cmap_name).copy()
    cmap.set_bad(alpha=0.0)
    hb = ax.hexbin(x_po, y_po, gridsize=gridsize, extent=_EXTENT, mincnt=0,
                   cmap=cmap, alpha=alpha, zorder=3)
    hb.set_array(diff)
    return hb


def freq_diff_chart(
    df_rs: pd.DataFrame,
    df_po: pd.DataFrame,
    title: str,
    gridsize: int = 20,
    fig_size: tuple = (12, 9),
    min_count: int = 5,
    cmap: str = "RdBu_r",
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Hexbin chart showing shot frequency differential: Playoffs minus Regular Season.

    Positive (red) = team shoots from there MORE in the playoffs.
    Negative (blue) = team shoots from there LESS in the playoffs.
    Bins with fewer than min_count combined shots are masked transparent.
    """
    x_rs, y_rs = df_rs["LOC_X"].to_numpy(), df_rs["LOC_Y"].to_numpy()
    x_po, y_po = df_po["LOC_X"].to_numpy(), df_po["LOC_Y"].to_numpy()
    n_rs, n_po = len(df_rs), len(df_po)

    rs_counts, po_counts = _measure_hexbin_grid(x_rs, y_rs, x_po, y_po, gridsize)

    rs_freq = rs_counts / rs_counts.sum()
    po_freq = po_counts / po_counts.sum()
    diff = (po_freq - rs_freq).astype(float)
    diff[rs_counts + po_counts < min_count] = np.nan

    abs_max = np.nanmax(np.abs(diff))

    fig, ax = plt.subplots(figsize=fig_size)
    ax.set_facecolor("#f8f8f8")
    draw_court(ax, color="#cccccc")

    hb = _apply_diff_to_hexbin(ax, x_po, y_po, diff, gridsize, cmap, alpha=0.85)
    hb.set_clim(-abs_max, abs_max)

    cb = plt.colorbar(hb, ax=ax, label="Shot frequency\n(Playoffs − Reg. Season)",
                      shrink=0.55, pad=0.02)
    cb.ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.1%}"))

    ax.set_title(
        f"{title}\nPlayoffs: {n_po} FGA  •  Regular Season: {n_rs} FGA",
        fontsize=13, fontweight="bold", pad=12,
    )
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", pad_inches=0.2)
    return fig, ax


def efficiency_diff_chart(
    df_rs: pd.DataFrame,
    df_po: pd.DataFrame,
    title: str,
    gridsize: int = 20,
    fig_size: tuple = (12, 9),
    min_count: int = 5,
    cmap: str = "RdBu_r",
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Hexbin chart showing shot efficiency differential: Playoffs minus Regular Season.

    Efficiency = pts per shot attempt (0, 2, or 3 per shot).
    Positive (red) = more efficient in playoffs. Negative (blue) = less efficient.
    Bins with fewer than min_count combined shots are masked transparent.
    """
    def _add_pts(df):
        df = df.copy()
        df["_pts"] = df["SHOT_MADE_FLAG"] * df["SHOT_TYPE"].str.contains("3PT").map({True: 3, False: 2})
        return df

    df_rs = _add_pts(df_rs)
    df_po = _add_pts(df_po)

    x_rs = df_rs["LOC_X"].to_numpy()
    y_rs = df_rs["LOC_Y"].to_numpy()
    pts_rs = df_rs["_pts"].to_numpy().astype(float)
    x_po = df_po["LOC_X"].to_numpy()
    y_po = df_po["LOC_Y"].to_numpy()
    pts_po = df_po["_pts"].to_numpy().astype(float)
    n_rs, n_po = len(df_rs), len(df_po)

    rs_pts_sum, rs_count, po_pts_sum, po_count = _measure_hexbin_pts(
        x_rs, y_rs, pts_rs, x_po, y_po, pts_po, gridsize
    )

    rs_eff = np.where(rs_count > 0, rs_pts_sum / rs_count, np.nan)
    po_eff = np.where(po_count > 0, po_pts_sum / po_count, np.nan)
    diff = (po_eff - rs_eff).astype(float)
    diff[rs_count + po_count < min_count] = np.nan

    # Symmetric clim at 95th percentile of abs values to avoid outlier distortion
    abs_vals = np.abs(diff[np.isfinite(diff)])
    abs_max = float(np.percentile(abs_vals, 95)) if len(abs_vals) else 1.0

    fig, ax = plt.subplots(figsize=fig_size)
    ax.set_facecolor("#f8f8f8")
    draw_court(ax, color="#cccccc")

    hb = _apply_diff_to_hexbin(ax, x_po, y_po, diff, gridsize, cmap, alpha=0.85)
    hb.set_clim(-abs_max, abs_max)

    cb = plt.colorbar(hb, ax=ax, label="Pts per shot attempt\n(Playoffs − Reg. Season)",
                      shrink=0.55, pad=0.02)
    cb.ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.2f}"))

    ax.set_title(
        f"{title}\nPlayoffs: {n_po} FGA  •  Regular Season: {n_rs} FGA",
        fontsize=13, fontweight="bold", pad=12,
    )
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", pad_inches=0.2)
    return fig, ax


# ── Smooth heatmap variants ───────────────────────────────────────────────────

_GRID_BINS = 200   # histogram resolution before smoothing
# Each bin = 500 units / 200 = 2.5 units = 0.25 ft.
# sigma=10 → ~2.5 ft blur radius, giving smooth zone-level blobs.
_SIGMA = 10.0
_X_EDGES = np.linspace(-250, 250, _GRID_BINS + 1)
_Y_EDGES = np.linspace(-47.5, 422.5, _GRID_BINS + 1)
_X_CENTERS = (_X_EDGES[:-1] + _X_EDGES[1:]) / 2
_Y_CENTERS = (_Y_EDGES[:-1] + _Y_EDGES[1:]) / 2


def _hist2d(x, y, weights=None):
    h, _, _ = np.histogram2d(x, y, bins=[_X_EDGES, _Y_EDGES], weights=weights)
    return h  # shape (X_BINS, Y_BINS)


def _smooth_chart_base(diff: np.ndarray, combined_cnt: np.ndarray, title: str,
                        cb_label: str, cb_fmt: str, n_rs: int, n_po: int,
                        cmap: str, fig_size: tuple, save_path):
    """Shared rendering for both smooth chart types."""
    # NaN-safe: fill before smoothing so gaussian_filter doesn't propagate NaNs.
    # The count-based mask below will hide regions with no real data.
    diff_smooth = gaussian_filter(np.nan_to_num(diff, nan=0.0), sigma=_SIGMA)

    # Mask using smoothed combined counts so the visible region follows the blur radius.
    cnt_smooth = gaussian_filter(combined_cnt, sigma=_SIGMA)
    diff_plot = np.where(cnt_smooth >= 0.3, diff_smooth, np.nan)

    valid = diff_plot[np.isfinite(diff_plot)]
    abs_max = float(np.nanpercentile(np.abs(valid), 97)) if len(valid) else 1.0

    fig, ax = plt.subplots(figsize=fig_size)
    ax.set_facecolor("#f8f8f8")

    cm = plt.get_cmap(cmap).copy()
    cm.set_bad(alpha=0.0)

    # pcolormesh needs the 2D array transposed: (Y, X) for (rows, cols)
    pcm = ax.pcolormesh(
        _X_CENTERS, _Y_CENTERS, diff_plot.T,
        cmap=cm, vmin=-abs_max, vmax=abs_max,
        shading="gouraud",   # bilinear interpolation → extra smooth look
        zorder=2,
    )

    draw_court(ax, color="#888888", lw=1.5)

    cb = plt.colorbar(pcm, ax=ax, label=cb_label, shrink=0.55, pad=0.02)
    cb.ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: cb_fmt.format(x=x)))

    ax.set_title(
        f"{title}\nPlayoffs: {n_po} FGA  •  Regular Season: {n_rs} FGA",
        fontsize=13, fontweight="bold", pad=12,
    )
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", pad_inches=0.2)
    return fig, ax


def smooth_freq_diff_chart(
    df_rs: pd.DataFrame,
    df_po: pd.DataFrame,
    title: str,
    fig_size: tuple = (12, 9),
    min_count: int = 5,
    cmap: str = "RdBu_r",
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Smooth heatmap showing shot frequency differential: Playoffs minus Regular Season.

    Uses a 2D histogram + Gaussian blur instead of discrete hexbins.
    Positive (red) = more shots in playoffs. Negative (blue) = fewer.
    """
    x_rs, y_rs = df_rs["LOC_X"].to_numpy(), df_rs["LOC_Y"].to_numpy()
    x_po, y_po = df_po["LOC_X"].to_numpy(), df_po["LOC_Y"].to_numpy()
    n_rs, n_po = len(df_rs), len(df_po)

    rs_hist = _hist2d(x_rs, y_rs)
    po_hist = _hist2d(x_po, y_po)

    rs_freq = rs_hist / rs_hist.sum()
    po_freq = po_hist / po_hist.sum()
    # Scale to "per 1000 shots" so colorbar shows readable numbers (~±1–5 range).
    diff = (po_freq - rs_freq) * 1000

    return _smooth_chart_base(
        diff, rs_hist + po_hist, title,
        cb_label="Extra shots per 1,000 FGA\n(Playoffs − Reg. Season)",
        cb_fmt="{x:+.2f}",
        n_rs=n_rs, n_po=n_po,
        cmap=cmap, fig_size=fig_size, save_path=save_path,
    )


def smooth_efficiency_diff_chart(
    df_rs: pd.DataFrame,
    df_po: pd.DataFrame,
    title: str,
    fig_size: tuple = (12, 9),
    min_count: int = 5,
    cmap: str = "RdBu_r",
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Smooth heatmap showing shot efficiency differential: Playoffs minus Regular Season.

    Efficiency = pts per shot attempt. Gaussian blur applied to pts and count
    histograms separately before dividing, which preserves spatial structure.
    Positive (red) = more efficient in playoffs. Negative (blue) = less efficient.
    """
    def _add_pts(df):
        df = df.copy()
        df["_pts"] = df["SHOT_MADE_FLAG"] * df["SHOT_TYPE"].str.contains("3PT").map({True: 3, False: 2})
        return df

    df_rs = _add_pts(df_rs)
    df_po = _add_pts(df_po)

    x_rs, y_rs = df_rs["LOC_X"].to_numpy(), df_rs["LOC_Y"].to_numpy()
    x_po, y_po = df_po["LOC_X"].to_numpy(), df_po["LOC_Y"].to_numpy()
    pts_rs = df_rs["_pts"].to_numpy().astype(float)
    pts_po = df_po["_pts"].to_numpy().astype(float)
    n_rs, n_po = len(df_rs), len(df_po)

    rs_cnt = _hist2d(x_rs, y_rs)
    rs_pts = _hist2d(x_rs, y_rs, weights=pts_rs)
    po_cnt = _hist2d(x_po, y_po)
    po_pts = _hist2d(x_po, y_po, weights=pts_po)

    # Smooth numerator and denominator separately before dividing
    rs_eff = np.where(
        gaussian_filter(rs_cnt, _SIGMA) > 0.1,
        gaussian_filter(rs_pts, _SIGMA) / gaussian_filter(rs_cnt, _SIGMA),
        np.nan,
    )
    po_eff = np.where(
        gaussian_filter(po_cnt, _SIGMA) > 0.1,
        gaussian_filter(po_pts, _SIGMA) / gaussian_filter(po_cnt, _SIGMA),
        np.nan,
    )
    diff = po_eff - rs_eff

    return _smooth_chart_base(
        diff, rs_cnt + po_cnt, title,
        cb_label="Pts per shot attempt\n(Playoffs − Reg. Season)",
        cb_fmt="{x:+.2f}",
        n_rs=n_rs, n_po=n_po,
        cmap=cmap, fig_size=fig_size, save_path=save_path,
    )


# --- Three-point zone chart -------------------------------------------------

# (SHOT_ZONE_BASIC, SHOT_ZONE_AREA, short label, label position)
_THREE_ZONES = [
    ("Left Corner 3", "Left Side(L)", "Left corner", (-215, -85)),
    ("Above the Break 3", "Left Side Center(LC)", "Left wing", (-205, 255)),
    ("Above the Break 3", "Center(C)", "Top of key", (0, 385)),
    ("Above the Break 3", "Right Side Center(RC)", "Right wing", (205, 255)),
    ("Right Corner 3", "Right Side(R)", "Right corner", (215, -85)),
]

_DIVERGING_3PT = ["#b8302a", "#e8a49b", "#f0efec", "#9dbbe0", "#2a62b0"]


def _three_zone_index(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Map court coordinates to an index into _THREE_ZONES (-1 = inside the arc)."""
    zone = np.full(x.shape, -1)
    corner = (np.abs(x) >= 220) & (y <= 92.5)
    above = (np.hypot(x, y) >= 237.5) & ~corner & (y > 0)
    ang = np.degrees(np.arctan2(y, x))
    zone[corner & (x < 0)] = 0
    zone[above & (ang >= 108)] = 1
    zone[above & (ang >= 72) & (ang < 108)] = 2
    zone[above & (ang < 72)] = 3
    zone[corner & (x > 0)] = 4
    return zone


def three_point_zone_chart(
    df: pd.DataFrame,
    league_avg: pd.DataFrame,
    title: str,
    subtitle: str = "",
    footer: str = "",
    max_diff: float = 10.0,
    fig_size: tuple = (10, 10),
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Three-point shot chart: each 3PT zone is shaded by FG% minus league average
    (red = below, blue = above), with every attempt plotted as a make or miss.

    Args:
        df:          Shot chart rows (all shots; 2PT attempts are dropped)
        league_avg:  LeagueAverages frame from ShotChartDetail
        max_diff:    Percentage-point difference at which the color saturates
    """
    from matplotlib.colors import LinearSegmentedColormap

    threes = df[df["SHOT_TYPE"] == "3PT Field Goal"]
    lg3 = league_avg.groupby(["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"])[["FGA", "FGM"]].sum()
    cmap = LinearSegmentedColormap.from_list("div3", _DIVERGING_3PT)

    # Per-zone team vs. league numbers
    zone_stats = []
    for basic, area, _, _ in _THREE_ZONES:
        z = threes[(threes["SHOT_ZONE_BASIC"] == basic) & (threes["SHOT_ZONE_AREA"] == area)]
        fgm, fga = int(z["SHOT_MADE_FLAG"].sum()), len(z)
        lg = lg3.loc[(basic, area)] if (basic, area) in lg3.index else None
        lg_pct = lg["FGM"] / lg["FGA"] * 100 if lg is not None and lg["FGA"] else np.nan
        pct = fgm / fga * 100 if fga else np.nan
        zone_stats.append((fgm, fga, pct, pct - lg_pct))

    fig, ax = plt.subplots(figsize=fig_size)

    # Zone fills: rasterize the court and color each pixel by its zone's differential
    gx, gy = np.meshgrid(np.linspace(-250, 250, 501), np.linspace(-47.5, 422.5, 471))
    zidx = _three_zone_index(gx, gy)
    fill = np.full(gx.shape, np.nan)
    for i, (_, _, _, diff) in enumerate(zone_stats):
        fill[zidx == i] = diff
    ax.imshow(
        np.ma.masked_invalid(fill), extent=_EXTENT, origin="lower",
        cmap=cmap, vmin=-max_diff, vmax=max_diff, alpha=0.85, zorder=1,
    )

    # Surface-colored gaps between zones
    gap = dict(color="white", lw=3, zorder=2)
    for side in (-1, 1):
        ax.plot([side * 220, side * 250], [92.5, 92.5], **gap)
        for deg in (72, 108):
            r = np.array([237.5, 470])
            ax.plot(r * np.cos(np.radians(deg)), r * np.sin(np.radians(deg)), **gap)

    draw_court(ax, color="#555555", lw=1.5)
    ax.set_ylim(-120, 422.5)

    made = threes[threes["SHOT_MADE_FLAG"] == 1]
    missed = threes[threes["SHOT_MADE_FLAG"] == 0]
    ax.scatter(missed["LOC_X"], missed["LOC_Y"], marker="x", s=36, c="#3a3a3a",
               linewidths=1.4, alpha=0.75, zorder=4, label=f"Missed ({len(missed)})")
    ax.scatter(made["LOC_X"], made["LOC_Y"], marker="o", s=60, c="#111111",
               edgecolors="white", linewidths=1.5, zorder=5, label=f"Made ({len(made)})")

    for (_, _, label, (lx, ly)), (fgm, fga, pct, diff) in zip(_THREE_ZONES, zone_stats):
        if not fga:
            continue
        ax.text(
            lx, ly, f"{label}\n{fgm}/{fga}  {pct:.0f}%\n{diff:+.1f} vs lg",
            ha="center", va="center", fontsize=9.5, color="#1a1a1a", zorder=6,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="none", alpha=0.9),
        )

    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=2,
              fontsize=9, frameon=False)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(-max_diff, max_diff))
    cb = plt.colorbar(sm, ax=ax, shrink=0.5, pad=0.02)
    cb.set_label("3P% vs. league average (pct. pts)")
    cb.ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.0f}"))

    ax.set_title(title, fontsize=15, fontweight="bold", pad=28)
    if subtitle:
        ax.text(0.5, 1.015, subtitle, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=10.5, color="#444444")
    if footer:
        ax.text(0.5, -0.01, footer, transform=ax.transAxes, ha="center",
                va="top", fontsize=9.5, color="#444444", linespacing=1.6)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="white")
    return fig, ax


# Net-rating tiers, best first: (label, lower bound, fill, text color)
_TIERS = [
    ("ELITE", 10, "#cfe3d8", "#2e6b52"),
    ("STRONG", 4, "#e1e8d3", "#5b6b3a"),
    ("MIDDLE", -4, "#e8e4dc", "#666666"),
    ("SHAKY", -10, "#f0e3cf", "#8a6236"),
    ("STRUGGLING", -np.inf, "#eed8d4", "#9a4a48"),
]
_TIER_BG = "#f6f2ea"
_TIER_INK = "#222222"
_TIER_ACCENT = "#2e7656"


def _spread_points(pts: np.ndarray, min_dist: float, bounds: tuple, iters: int = 400) -> np.ndarray:
    """Nudge overlapping points apart while pulling each gently back to its anchor."""
    pos = pts.astype(float).copy()
    lo, hi = bounds
    for _ in range(iters):
        delta = pos[:, None, :] - pos[None, :, :]
        dist = np.hypot(delta[..., 0], delta[..., 1])
        np.fill_diagonal(dist, np.inf)
        overlap = np.clip(min_dist - dist, 0, None)
        if not overlap.any():
            break
        push = (delta / np.where(dist == 0, 1e-6, dist)[..., None]) * overlap[..., None] / 2
        pos += push.sum(axis=1) + 0.02 * (pts - pos)
        pos = np.clip(pos, lo + min_dist / 2, hi - min_dist / 2)
    return pos


def team_tiers_chart(
    df: pd.DataFrame,
    logos: dict,
    league_avg: float,
    tag: str,
    note: str = "",
    credit: str = "",
    fig_size: tuple = (9, 16),
    logo_in: float = 0.5,
    save_path: str | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """
    Portrait offense-vs-defense scatter: ORtg on x, DRtg on y (inverted, so better
    defense is up), team logos as markers, diagonal bands shading net-rating tiers.

    Args:
        df:          Rows with abbreviation, OFF_RATING, DEF_RATING
        logos:       abbreviation -> RGBA array
        league_avg:  League points per 100 possessions; drawn as the dashed reference lines
        tag:         Text for the banner above the title, e.g. "ENTERING OCT 28"
        logo_in:     Logo size in inches
    """
    from matplotlib.offsetbox import AnnotationBbox, OffsetImage
    from matplotlib.patches import Rectangle

    plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]  # DejaVu covers the ↗
    fig = plt.figure(figsize=fig_size, facecolor=_TIER_BG)

    # Header
    fig.patches.append(Rectangle((0.06, 0.948), 0.29, 0.03, transform=fig.transFigure,
                                 fc=_TIER_ACCENT, ec="none"))
    fig.text(0.205, 0.963, tag, ha="center", va="center", fontsize=15,
             fontweight="bold", color="white")
    fig.text(0.06, 0.905, "NBA TEAM TIERS", ha="left", va="center", fontsize=46,
             fontweight="bold", color=_TIER_INK)
    fig.add_artist(plt.Line2D([0.06, 0.94], [0.866, 0.866], color="#cfc8ba", lw=1))
    fig.text(0.065, 0.845, "RATING / 100 POSS.", ha="left", va="center", fontsize=13,
             fontweight="bold", color=_TIER_INK)
    fig.text(0.935, 0.845, "BETTER TEAMS  ↗", ha="right", va="center", fontsize=13,
             fontweight="bold", color=_TIER_ACCENT)

    # Fit the axes to the teams, then widen the tighter axis so a rating point is the
    # same length both ways (keeps the tier bands at 45°)
    ax_rect = [0.12, 0.275, 0.82, 0.545]
    ax_w_in, ax_h_in = ax_rect[2] * fig_size[0], ax_rect[3] * fig_size[1]
    pad = 2.0
    pts = df[["OFF_RATING", "DEF_RATING"]].to_numpy()
    mid = (pts.min(axis=0) + pts.max(axis=0)) / 2
    span = pts.max(axis=0) - pts.min(axis=0) + 2 * pad
    units_per_in = max(span[0] / ax_w_in, span[1] / ax_h_in)
    half = units_per_in * np.array([ax_w_in, ax_h_in]) / 2
    lo, hi = mid - half, mid + half  # per axis: [x, y]

    ax = fig.add_axes(ax_rect)
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(hi[1], lo[1])  # lower DRtg is better, so it goes on top
    ax.set_aspect("equal")
    ax.set_facecolor(_TIER_BG)

    # Tier bands: net = ORtg - DRtg, so each boundary is the line DRtg = ORtg - bound
    xs = np.array([lo.min() - 50, hi.max() + 50])
    bounds = [np.inf] + [t[1] for t in _TIERS]
    for (_, floor, fill, _), ceiling in zip(_TIERS, bounds):
        ax.fill_between(xs, xs - np.clip(ceiling, -100, 100), xs - np.clip(floor, -100, 100),
                        color=fill, lw=0, zorder=0)
        if np.isfinite(floor):
            ax.plot(xs, xs - floor, color="#c9c2b4", lw=0.8, zorder=1)

    ax.axvline(league_avg, color="#9a9488", lw=1, ls=(0, (4, 4)), zorder=1)
    ax.axhline(league_avg, color="#9a9488", lw=1, ls=(0, (4, 4)), zorder=1)
    ax.text(league_avg + 0.3, hi[1] - 0.4, f"LG AVG {league_avg:.1f}", ha="left", va="bottom",
            fontsize=9, color="#7d776c")

    # Logos, nudged apart where they collide, with a leader line back to the true spot
    size = logo_in * units_per_in
    anchors = pts
    placed = _spread_points(anchors, size * 1.08, (lo, hi))
    for abbr, (ax0, ay0), (px, py) in zip(df["abbreviation"], anchors, placed):
        if np.hypot(px - ax0, py - ay0) > size * 0.15:
            ax.plot([ax0, px], [ay0, py], color="#77716a", lw=1, zorder=2)
            ax.scatter([ax0], [ay0], s=14, color="#77716a", zorder=2, lw=0)
        img = logos[abbr]
        zoom = logo_in * 72 / max(img.shape[:2])
        ax.add_artist(AnnotationBbox(OffsetImage(img, zoom=zoom), (px, py),
                                     frameon=False, zorder=3))

    ax.set_xticks(np.arange(np.ceil(lo[0] / 5) * 5, hi[0], 5))
    ax.set_yticks(np.arange(np.ceil(lo[1] / 5) * 5, hi[1], 5))
    ax.tick_params(length=0, labelsize=12, labelcolor="#6b665d", pad=8)
    for spine in ax.spines.values():
        spine.set_color("#cfc8ba")
    ax.set_xlabel("OFFENSIVE RATING  →", fontsize=14, fontweight="bold",
                  color=_TIER_INK, labelpad=14)
    ax.set_ylabel("DEFENSIVE RATING  →", fontsize=14, fontweight="bold",
                  color=_TIER_INK, labelpad=14)

    # Tier legend
    fig.text(0.065, 0.2, "TIERS BY NET RATING", ha="left", va="center", fontsize=14,
             fontweight="bold", color=_TIER_INK)
    box_w, gap = 0.162, 0.0125
    for i, ((label, floor, fill, ink), ceiling) in enumerate(zip(_TIERS, bounds)):
        x0 = 0.062 + i * (box_w + gap)
        fig.patches.append(Rectangle((x0, 0.157), box_w, 0.026, transform=fig.transFigure,
                                     fc=fill, ec="none"))
        fig.text(x0 + box_w / 2, 0.17, label, ha="center", va="center", fontsize=12,
                 fontweight="bold", color=ink)
        if not np.isfinite(ceiling):
            rng = f"≥ +{floor}"
        elif not np.isfinite(floor):
            rng = f"< −{abs(ceiling)}"
        else:
            rng = f"{floor:+d} to {ceiling:+d}".replace("-", "−")
        fig.text(x0 + box_w / 2, 0.14, rng, ha="center", va="center", fontsize=11,
                 color="#6b665d")

    if note:
        fig.text(0.065, 0.098, note, ha="left", va="center", fontsize=10.5,
                 color="#6b665d", linespacing=1.5)
    fig.text(0.065, 0.05, "SOURCE: NBA.COM/STATS", ha="left", va="center", fontsize=12,
             fontweight="bold", color="#77716a")
    if credit:
        fig.text(0.935, 0.05, credit, ha="right", va="center", fontsize=12,
                 fontweight="bold", color="#77716a")

    if save_path:
        fig.savefig(save_path, dpi=240, facecolor=_TIER_BG)
    return fig, ax
