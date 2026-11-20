"""
Knicks under Mike Brown: the starting five (Brunson, Bridges, Anunoby, Towns + Josh Hart)
vs. the same four with Landry Shamet in Hart's spot. 2025-26 regular season, 2026 playoffs,
2026-27 regular season to date.

Produces six landscape PNGs (sized for a Substack post):
  knicks_lineup_net_rating.png     — net rating by sample, with rough error bars
  knicks_lineup_four_factors.png   — how each lineup wins (all three samples pooled)
  knicks_matchup_difficulty.png    — how good the players each Knick guards are
  knicks_opponent_strength.png     — how often each lineup faces the opponent's top five
  knicks_rank_changes.png          — team league ranks, 2025-26 → 2026-27
  knicks_starters_playoffs.png     — the starting five, regular season vs. playoffs

Run from the repo root:
    .venv/bin/python examples/knicks_lineup_post.py
"""
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from nba_api.stats.endpoints import (
    BoxScoreMatchupsV3,
    GameRotation,
    LeagueDashLineups,
    LeagueDashPlayerStats,
    LeagueDashTeamStats,
    LeagueGameFinder,
    LeagueSeasonMatchups,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from nba_shot_charts.data.cache import cache_path, load_from_cache, save_to_cache  # noqa: E402

CREDIT = "WARD WALTON"
NYK = 1610612752
CURRENT = "2026-27"  # in progress: season aggregates are re-fetched every run

BRUNSON, BRIDGES, ANUNOBY, TOWNS = 1628973, 1628969, 1628384, 1626157
HART, SHAMET = 1628404, 1629013
CORE = {BRUNSON, BRIDGES, ANUNOBY, TOWNS}

SAMPLES = [  # (season, season type, short label)
    ("2025-26", "Regular Season", "2025-26 REG. SEASON"),
    ("2025-26", "Playoffs", "2026 PLAYOFFS"),
    ("2026-27", "Regular Season", "2026-27 SO FAR"),
]

# ── palette (validated on the cream surface; orange/aqua < 3:1, so every mark is labeled) ──
BG = "#f6f2ea"
INK = "#222222"
MUTED = "#6b665d"
FAINT = "#77716a"
RULE = "#cfc8ba"
GRID = "#e4ddcf"
HART_C = "#2a78d6"     # starters (with Hart)
SHAMET_C = "#eb6834"   # Shamet lineup
OTHER_C = "#b9b2a5"    # everything else / de-emphasized
SAMPLE_C = ["#6250d6", "#1baf7a", "#eda100"]  # seasons: violet, aqua, yellow (validated set)

plt.rcParams["font.family"] = ["Arial", "DejaVu Sans"]


# ═════════════════════════════════════════════════════════════════════════════
# Data
# ═════════════════════════════════════════════════════════════════════════════

def _fetch(fn, **kwargs):
    for attempt in range(4):
        try:
            time.sleep(0.7)
            return fn(timeout=60, **kwargs).get_data_frames()
        except Exception as exc:  # stats.nba.com drops connections now and then
            if attempt == 3:
                raise
            print(f"  retrying {fn.__name__}: {exc}")
            time.sleep(5)


def _cached(key: str, season: str, build) -> pd.DataFrame:
    path = cache_path(key)
    df = None if season == CURRENT else load_from_cache(path)
    if df is None:
        df = build()
        save_to_cache(df, path)
    return df


def _tag(season, st):
    return f"{season}_{st.replace(' ', '_')}"


def knicks_lineups(season, st) -> pd.DataFrame:
    """Every Knicks 5-man lineup: Base + Advanced + Four Factors + Opponent, totals."""
    def build():
        frames = {mt: _fetch(LeagueDashLineups, team_id_nullable=NYK, season=season,
                             season_type_all_star=st, group_quantity=5,
                             measure_type_detailed_defense=mt, per_mode_detailed="Totals")[0]
                  for mt in ["Base", "Advanced", "Four Factors", "Opponent"]}
        df = frames.pop("Base")
        for f in frames.values():
            df = df.merge(f[[c for c in f.columns if c not in df.columns or c == "GROUP_ID"]],
                          on="GROUP_ID")
        return df
    df = _cached(f"post_nyk_lineups5_{_tag(season, st)}", season, build)
    ids = df["GROUP_ID"].str.strip("-").str.split("-")
    df["IDS"] = ids.map(lambda x: frozenset(int(i) for i in x))
    return df


def knicks_games(season, st) -> pd.DataFrame:
    return _cached(f"post_nyk_games_{_tag(season, st)}", season, lambda: _fetch(
        LeagueGameFinder, team_id_nullable=NYK, season_nullable=season,
        season_type_nullable=st, league_id_nullable="00")[0])


def rotation(game_id) -> pd.DataFrame:
    # A finished game's rotation never changes, so these are always cached
    path = cache_path(f"rotation_{game_id}")
    df = load_from_cache(path)
    if df is None:
        df = pd.concat(_fetch(GameRotation, game_id=game_id))
        save_to_cache(df, path)
    return df


def player_stats(season, st) -> pd.DataFrame:
    return _cached(f"post_players_{_tag(season, st)}", season, lambda: _fetch(
        LeagueDashPlayerStats, season=season, season_type_all_star=st,
        per_mode_detailed="PerGame")[0])


def team_stats(season, st) -> pd.DataFrame:
    def build():
        adv, ff, opp = (_fetch(LeagueDashTeamStats, season=season, season_type_all_star=st,
                               measure_type_detailed_defense=mt)[0]
                        for mt in ["Advanced", "Four Factors", "Opponent"])
        df = adv.merge(ff[["TEAM_ID", "FTA_RATE", "OPP_EFG_PCT", "OPP_TOV_PCT"]], on="TEAM_ID")
        return df.merge(opp[["TEAM_ID", "OPP_FG3M", "OPP_FG3A"]], on="TEAM_ID")
    return _cached(f"post_teams_{_tag(season, st)}", season, build)


def knicks_matchups(season, st) -> pd.DataFrame:
    """Defender → offensive player partial possessions for every Knicks defender."""
    def build():
        if st == "Regular Season":
            df = _fetch(LeagueSeasonMatchups, season=season, season_type_playoffs=st,
                        def_team_id_nullable=NYK)[0]
            return df[["OFF_PLAYER_ID", "DEF_PLAYER_ID", "PARTIAL_POSS", "PLAYER_PTS"]]
        # The season-matchups endpoint returns nothing for the playoffs; build it per game
        games = knicks_games(season, st)
        box = pd.concat(_fetch(BoxScoreMatchupsV3, game_id=g)[0] for g in games["GAME_ID"])
        box = box[box["teamId"] != NYK]  # rows are keyed by the offense's team
        return (box.groupby(["personIdOff", "personIdDef"], as_index=False)
                .agg(PARTIAL_POSS=("partialPossessions", "sum"), PLAYER_PTS=("playerPoints", "sum"))
                .rename(columns={"personIdOff": "OFF_PLAYER_ID", "personIdDef": "DEF_PLAYER_ID"}))
    return _cached(f"post_nyk_matchups_{_tag(season, st)}", season, build)


def stints(season, st) -> pd.DataFrame:
    """
    Every stretch of game time with no substitution: which five Knicks were on, and how
    many of the opponent's five highest-minute players that night were on with them.
    """
    rows = []
    for gid in knicks_games(season, st)["GAME_ID"]:
        r = rotation(gid)
        opp = r[r["TEAM_ID"] != NYK]
        opp_min = (opp["OUT_TIME_REAL"] - opp["IN_TIME_REAL"]).groupby(opp["PERSON_ID"]).sum()
        top5 = set(opp_min.nlargest(5).index)
        cuts = sorted(set(r["IN_TIME_REAL"]) | set(r["OUT_TIME_REAL"]))
        for a, b in zip(cuts[:-1], cuts[1:]):
            mid = (a + b) / 2
            on = r[(r["IN_TIME_REAL"] <= mid) & (r["OUT_TIME_REAL"] > mid)]
            k = frozenset(on.loc[on["TEAM_ID"] == NYK, "PERSON_ID"])
            o = set(on.loc[on["TEAM_ID"] != NYK, "PERSON_ID"])
            if len(k) == 5 and len(o) == 5:
                rows.append({"sec": (b - a) / 10, "nyk": k, "opp_top5": len(o & top5)})
    return pd.DataFrame(rows)


def which_lineup(ids) -> str:
    if not CORE <= ids:
        return "other"
    fifth = next(iter(ids - CORE))
    return {HART: "hart", SHAMET: "shamet"}.get(fifth, "other")


# ── derived tables ──────────────────────────────────────────────────────────

RATE_COLS = ["OREB_PCT", "DREB_PCT", "TM_TOV_PCT", "OPP_TOV_PCT", "PACE"]


def lineup_summary(rows: pd.DataFrame) -> pd.Series:
    """Pool one or more lineup rows: counting stats summed, API rates possession-weighted."""
    s = rows[["MIN", "POSS", "PTS", "PLUS_MINUS", "FGM", "FGA", "FG3M", "FG3A", "FTA",
              "OPP_FGM", "OPP_FGA", "OPP_FG3M", "OPP_FG3A"]].sum()
    w = rows["POSS"]
    out = {c: np.average(rows[c], weights=w) for c in RATE_COLS}
    # Ratings: NBA.com's own per-lineup figures (they count each side's possessions
    # separately, so they don't equal plus-minus / POSS), possession-weighted when pooled
    out.update(
        MIN=s["MIN"], POSS=s["POSS"],
        ORTG=np.average(rows["OFF_RATING"], weights=w),
        DRTG=np.average(rows["DEF_RATING"], weights=w),
        EFG=(s["FGM"] + 0.5 * s["FG3M"]) / s["FGA"],
        OPP_EFG=(s["OPP_FGM"] + 0.5 * s["OPP_FG3M"]) / s["OPP_FGA"],
        FT_RATE=s["FTA"] / s["FGA"], FG3_PCT=s["FG3M"] / s["FG3A"],
        OPP_FG3_PCT=s["OPP_FG3M"] / s["OPP_FG3A"],
    )
    out["NET"] = np.average(rows["NET_RATING"], weights=w)
    # Rough 1-SE on net rating: ~1.6 pts SD per possession pair → 160 / √poss per 100
    out["NET_SE"] = 160 / np.sqrt(s["POSS"])
    return pd.Series(out)


def load_all():
    lineups, opp_strength, matchups = {}, {}, {}
    for season, st, label in SAMPLES:
        print(f"Loading {season} {st} ...")
        lu = knicks_lineups(season, st)
        lu["WHICH"] = lu["IDS"].map(which_lineup)
        lineups[label] = lu

        stn = stints(season, st)
        stn["WHICH"] = stn["nyk"].map(which_lineup)
        opp_strength[label] = stn.groupby("WHICH").apply(
            lambda x: np.average(x["opp_top5"] >= 4, weights=x["sec"]), include_groups=False)

        pl = player_stats(season, st)
        m = knicks_matchups(season, st).merge(
            pl[["PLAYER_ID", "PTS"]].rename(columns={"PLAYER_ID": "OFF_PLAYER_ID", "PTS": "OFF_PPG"}),
            on="OFF_PLAYER_ID")
        matchups[label] = m.groupby("DEF_PLAYER_ID").apply(
            lambda x: pd.Series({"OPP_PPG": np.average(x["OFF_PPG"], weights=x["PARTIAL_POSS"]),
                                 "POSS": x["PARTIAL_POSS"].sum()}), include_groups=False)
    return lineups, opp_strength, matchups


# ═════════════════════════════════════════════════════════════════════════════
# Chart scaffolding (house style: cream card, bold caps title, source + byline)
# ═════════════════════════════════════════════════════════════════════════════

FIGSIZE = (11, 7.2)


def frame(kicker: str, title: str, subtitle: str, note: str):
    fig = plt.figure(figsize=FIGSIZE, facecolor=BG)
    fig.text(0.055, 0.945, kicker, ha="left", va="center", fontsize=12.5,
             fontweight="bold", color=HART_C)
    fig.text(0.055, 0.885, title, ha="left", va="center", fontsize=28,
             fontweight="bold", color=INK)
    fig.text(0.055, 0.822, subtitle, ha="left", va="center", fontsize=13, color=MUTED)
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.785, 0.785], color=RULE, lw=1))
    fig.add_artist(plt.Line2D([0.055, 0.945], [0.095, 0.095], color=RULE, lw=1))
    fig.text(0.055, 0.06, note, ha="left", va="center", fontsize=9.5, color=MUTED,
             linespacing=1.45)
    fig.text(0.055, 0.022, "SOURCE: NBA.COM/STATS", ha="left", va="center", fontsize=10,
             fontweight="bold", color=FAINT)
    fig.text(0.945, 0.022, CREDIT, ha="right", va="center", fontsize=10,
             fontweight="bold", color=FAINT)
    return fig


def style_ax(ax, grid_axis="y"):
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0, labelsize=11.5, labelcolor=MUTED, pad=6)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def legend_chips(fig, items, x, y, size=11.5):
    """Inline legend: colored square + label, left to right."""
    for color, label in items:
        fig.patches.append(plt.Rectangle((x, y - 0.011), 0.014, 0.022, transform=fig.transFigure,
                                         color=color, lw=0, figure=fig))
        t = fig.text(x + 0.02, y, label, ha="left", va="center", fontsize=size,
                     fontweight="bold", color=INK)
        fig.canvas.draw()
        bb = t.get_window_extent().transformed(fig.transFigure.inverted())
        x = bb.x1 + 0.03


def save(fig, name):
    fig.savefig(name, dpi=200, facecolor=BG)
    plt.close(fig)
    print(f"Saved {name}")


def bar(ax, x, h, w, color, bottom=0):
    """Thin bar with its value end rounded slightly; 2px surface gap via edgecolor."""
    return ax.bar(x, h, w, bottom=bottom, color=color, edgecolor=BG, linewidth=1.5, zorder=3)


# ═════════════════════════════════════════════════════════════════════════════
# Charts
# ═════════════════════════════════════════════════════════════════════════════

def chart_net_rating(lineups):
    groups = [(label, lu) for label, lu in lineups.items()]
    groups.append(("ALL THREE COMBINED", pd.concat(lineups.values())))
    hart_min = sum(lu.loc[lu["WHICH"] == "hart", "MIN"].sum() for lu in lineups.values())
    sham_min = sum(lu.loc[lu["WHICH"] == "shamet", "MIN"].sum() for lu in lineups.values())

    fig = frame("THE KNICKS UNDER MIKE BROWN",
                "Shamet's lineup has the better number",
                f"Same four starters. Hart's version has played {hart_min:,.0f} minutes; "
                f"Shamet's has played {sham_min:,.0f}.",
                "Net rating = points scored minus points allowed per 100 possessions. The four: "
                "Brunson, Bridges, Anunoby, Towns.\nWhiskers = ±1 standard error, a rough guide "
                "to how much a sample this size could move by chance.")
    ax = fig.add_axes([0.07, 0.2, 0.88, 0.5])
    style_ax(ax)
    w = 0.34
    for i, (label, lu) in enumerate(groups):
        for j, (which, color) in enumerate([("hart", HART_C), ("shamet", SHAMET_C)]):
            s = lineup_summary(lu[lu["WHICH"] == which])
            x = i + (j - 0.5) * (w + 0.03)
            bar(ax, x, s["NET"], w, color)
            ax.errorbar(x, s["NET"], yerr=s["NET_SE"], color=INK, lw=1, capsize=0, zorder=4)
            va, off = ("bottom", s["NET_SE"] + 1.5) if s["NET"] >= 0 else ("top", -s["NET_SE"] - 1.5)
            ax.text(x, s["NET"] + off, f"{s['NET']:+.1f}", ha="center", va=va, fontsize=12,
                    fontweight="bold", color=INK, zorder=5)
            ax.text(x, -0.012, f"{s['POSS']:,.0f}\nposs.", ha="center", va="top",
                    transform=ax.get_xaxis_transform(), fontsize=9, color=FAINT)
    ax.axhline(0, color=FAINT, lw=1, zorder=4)
    ax.set_ylim(min(ax.get_ylim()[0], -32), ax.get_ylim()[1])
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([g[0] for g in groups], fontsize=11.5, fontweight="bold", color=INK)
    ax.tick_params(axis="x", pad=34)
    ax.axvline(len(groups) - 1.5, color=RULE, lw=1)
    ax.set_ylabel("NET RATING", fontsize=11, fontweight="bold", color=INK)
    ax.set_xlim(-0.6, len(groups) - 0.4)
    legend_chips(fig, [(HART_C, "Four + Josh Hart (starters)"), (SHAMET_C, "Four + Landry Shamet")],
                 0.055, 0.75)
    save(fig, "knicks_lineup_net_rating.png")


def small_multiples(fig, panels, series, top=0.64, bottom=0.15):
    """
    panels: list of (title, better-direction text, [value per series], formatter)
    series: list of (label, color)
    """
    ncol, nrow = 4, int(np.ceil(len(panels) / 4))
    left, right, hgap, vgap = 0.055, 0.945, 0.035, 0.1
    pw = (right - left - hgap * (ncol - 1)) / ncol
    ph = (top - bottom - vgap * (nrow - 1)) / nrow
    for k, (title, better, vals, fmt) in enumerate(panels):
        r, c = divmod(k, ncol)
        ax = fig.add_axes([left + c * (pw + hgap), top - (r + 1) * ph - r * vgap, pw, ph])
        style_ax(ax, grid_axis=None)
        hi = max(vals)
        floor = 0  # bars always start at zero, so heights stay honest
        pad = hi * 0.12
        for i, (v, (_, color)) in enumerate(zip(vals, series)):
            ax.bar(i, v, 0.62, color=color, edgecolor=BG, linewidth=1.5, zorder=3)
            ax.text(i, v, fmt(v), ha="center", va="bottom", fontsize=12.5, fontweight="bold",
                    color=INK, zorder=4)
        ax.set_ylim(floor, hi + pad * 2)
        ax.set_xlim(-0.6, len(vals) - 0.4)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axhline(floor, color=FAINT, lw=1, zorder=2)
        ax.set_title(title, loc="left", fontsize=11.5, fontweight="bold", color=INK, pad=20)
        ax.text(0, 1.04, better, transform=ax.transAxes, fontsize=9, color=FAINT, va="bottom")


PCT = lambda v: f"{100 * v:.1f}%"  # noqa: E731
ONE = lambda v: f"{v:.1f}"  # noqa: E731

FACTOR_PANELS = [  # (title, better, key, fmt)
    ("Effective FG%", "higher is better", "EFG", PCT),
    ("Opponent eFG%", "lower is better", "OPP_EFG", PCT),
    ("Offensive reb. %", "higher is better", "OREB_PCT", PCT),
    ("Defensive reb. %", "higher is better", "DREB_PCT", PCT),
    ("Turnover %", "lower is better", "TM_TOV_PCT", PCT),
    ("Opp. turnover %", "higher is better", "OPP_TOV_PCT", PCT),
    ("FT attempts per FGA", "higher is better", "FT_RATE", lambda v: f"{v:.2f}"),
    ("Opponent 3P%", "lower is better · mostly luck", "OPP_FG3_PCT", PCT),
]


def chart_four_factors(lineups):
    alls = pd.concat(lineups.values())
    h = lineup_summary(alls[alls["WHICH"] == "hart"])
    s = lineup_summary(alls[alls["WHICH"] == "shamet"])
    fig = frame("HOW EACH LINEUP WINS",
                "Shamet's lineup shoots worse, but gets more chances",
                "All three samples combined: 2025-26, the 2026 playoffs, 2026-27 so far.",
                f"Hart lineup {h['POSS']:,.0f} possessions, Shamet lineup {s['POSS']:,.0f}. "
                "Rebound and turnover rates are possession-weighted NBA.com figures.\n"
                "Opponent 3P% swings a lot in samples this small and is mostly outside a "
                "lineup's control.")
    series = [("Hart", HART_C), ("Shamet", SHAMET_C)]
    panels = [(t, b, [h[k], s[k]], f) for t, b, k, f in FACTOR_PANELS]
    small_multiples(fig, panels, series)
    legend_chips(fig, [(HART_C, "Four + Hart"), (SHAMET_C, "Four + Shamet")], 0.055, 0.75)
    save(fig, "knicks_lineup_four_factors.png")


def chart_starters_playoffs(lineups):
    rs = lineups[SAMPLES[0][2]]
    po = lineups[SAMPLES[1][2]]
    a = lineup_summary(rs[rs["WHICH"] == "hart"])
    b = lineup_summary(po[po["WHICH"] == "hart"])
    fig = frame("THE TITLE RUN",
                "The starters' defense got better in the playoffs",
                f"Brunson-Bridges-Anunoby-Towns-Hart. Net rating {a['NET']:+.1f} in the "
                f"regular season, {b['NET']:+.1f} in the playoffs.",
                f"2025-26 regular season: {a['POSS']:,.0f} possessions. 2026 playoffs: "
                f"{b['POSS']:,.0f}. Defensive rating went from {a['DRTG']:.1f} to "
                f"{b['DRTG']:.1f}; offense barely moved\n({a['ORTG']:.1f} → {b['ORTG']:.1f}). "
                "Every playoff minute came against a playoff team.")
    series = [("Regular season", OTHER_C), ("Playoffs", HART_C)]
    panels = [(t, bt, [a[k], b[k]], f) for t, bt, k, f in FACTOR_PANELS]
    small_multiples(fig, panels, series)
    legend_chips(fig, [(OTHER_C, "2025-26 regular season"), (HART_C, "2026 playoffs")], 0.055, 0.75)
    save(fig, "knicks_starters_playoffs.png")


def chart_matchup_difficulty(matchups):
    players = [(HART, "Josh Hart"), (SHAMET, "Landry Shamet"), (ANUNOBY, "OG Anunoby"),
               (BRIDGES, "Mikal Bridges"), (BRUNSON, "Jalen Brunson"), (TOWNS, "Karl-Anthony Towns")]
    first = matchups[SAMPLES[0][2]]
    players.sort(key=lambda p: first.loc[p[0], "OPP_PPG"])
    fig = frame("WHO THEY GUARD",
                "Hart draws tougher assignments than Shamet",
                "Average scoring of the players each Knick defended, weighted by possessions "
                "spent guarding them.",
                "Player-tracking matchup data. Each opponent is rated by his points per game in "
                "that sample (regular season or playoffs).\nHart's most-guarded: Barnes, Ingram, "
                "Jalen Johnson, Paul George, Tatum, LeBron. Shamet's: Nesmith, Powell, "
                "Maxey, Donovan Mitchell, Fox.")
    ax = fig.add_axes([0.2, 0.18, 0.74, 0.52])
    style_ax(ax, grid_axis="x")
    ys = np.arange(len(players))
    for i, (pid, name) in enumerate(players):
        highlight = pid in (HART, SHAMET)
        if highlight:
            ax.axhspan(i - 0.42, i + 0.42, color="#ece5d6", zorder=0, lw=0)
        vals = [m.loc[pid, "OPP_PPG"] for m in matchups.values()]
        ax.plot([min(vals), max(vals)], [i, i], color=RULE, lw=2, zorder=2)
        for v, color in zip(vals, SAMPLE_C):
            ax.scatter(v, i, s=110, color=color, edgecolor=BG, linewidth=2, zorder=3)
            if highlight:
                ax.text(v, i - 0.17, f"{v:.1f}", ha="center", va="top", fontsize=10,
                        fontweight="bold", color=INK, zorder=4)
    ax.set_yticks(ys)
    ax.set_yticklabels([p[1] for p in players], fontsize=12.5)
    for lbl, (pid, _) in zip(ax.get_yticklabels(), players):
        lbl.set_color(INK)
        lbl.set_fontweight("bold" if pid in (HART, SHAMET) else "normal")
    ax.set_ylim(-0.6, len(players) - 0.4)
    ax.set_xlabel("POINTS PER GAME OF THE PLAYER BEING GUARDED  →  HARDER", fontsize=11,
                  fontweight="bold", color=INK, labelpad=10)
    legend_chips(fig, list(zip(SAMPLE_C, ["2025-26 regular season", "2026 playoffs",
                                           "2026-27 so far"])), 0.055, 0.75)
    save(fig, "knicks_matchup_difficulty.png")


def chart_opponent_strength(opp_strength):
    fig = frame("WHO'S ON THE OTHER SIDE",
                "Shamet's lineup isn't just beating benches",
                "Share of each lineup's minutes played against at least four of the opponent's "
                "five highest-minute players that night.",
                "Only in 2025-26 did the starters see clearly tougher units. In the playoffs and "
                "this season, Shamet's minutes came against starter-heavy lineups too.\nBuilt "
                "from NBA.com game rotation data; the lineup minutes it produces match NBA.com's "
                "official lineup totals.")
    ax = fig.add_axes([0.07, 0.17, 0.88, 0.52])
    style_ax(ax)
    series = [("hart", HART_C, "Four + Hart"), ("shamet", SHAMET_C, "Four + Shamet"),
              ("other", OTHER_C, "All other Knicks lineups")]
    w = 0.25
    for i, (label, s) in enumerate(opp_strength.items()):
        for j, (key, color, _) in enumerate(series):
            x = i + (j - 1) * (w + 0.02)
            bar(ax, x, 100 * s[key], w, color)
            ax.text(x, 100 * s[key] + 1.5, f"{100 * s[key]:.0f}%", ha="center", va="bottom",
                    fontsize=12, fontweight="bold", color=INK)
    ax.set_xticks(range(len(opp_strength)))
    ax.set_xticklabels(list(opp_strength), fontsize=11.5, fontweight="bold", color=INK)
    ax.set_ylim(0, 105)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.axhline(0, color=FAINT, lw=1)
    legend_chips(fig, [(c, n) for _, c, n in series], 0.055, 0.75)
    save(fig, "knicks_opponent_strength.png")


def chart_rank_changes():
    metrics = [  # (label, column, lower-is-better)
        ("Offensive rating", "OFF_RATING", False), ("Defensive rating", "DEF_RATING", True),
        ("Effective FG%", "EFG_PCT", False), ("Opponent eFG%", "OPP_EFG_PCT", True),
        ("Offensive reb. %", "OREB_PCT", False), ("Defensive reb. %", "DREB_PCT", False),
        ("Assist %", "AST_PCT", False), ("Forced turnover %", "OPP_TOV_PCT", False),
        ("FT attempts per FGA", "FTA_RATE", False), ("Pace (fastest = 1)", "PACE", False),
    ]
    ranks = {}
    for season in ["2025-26", "2026-27"]:
        t = team_stats(season, "Regular Season")
        nyk = t.index[t["TEAM_ID"] == NYK][0]
        gp = int(t.loc[nyk, "GP"])
        ranks[season] = {lbl: int(t[col].rank(ascending=low, method="min")[nyk])
                         for lbl, col, low in metrics}
    fig = frame("WHAT'S CHANGED",
                "Same roster, different identity",
                "Knicks league rank (1 = best of 30), 2025-26 regular season vs. 2026-27 so far.",
                f"2026-27 through {gp} games. For pace, rank 1 = fastest; it is "
                "a style marker, not good or bad.\nBlue = rank improved, orange = rank fell, "
                "gray = within two spots.")
    ax = fig.add_axes([0.2, 0.15, 0.6, 0.58])
    style_ax(ax, grid_axis=None)
    for lbl, _, _ in metrics:
        a, b = ranks["2025-26"][lbl], ranks["2026-27"][lbl]
        if lbl.startswith("Pace") or abs(a - b) <= 2:
            color, lw = OTHER_C, 2
        else:
            color, lw = (HART_C if b < a else SHAMET_C), 2.5
        ax.plot([0, 1], [a, b], color=color, lw=lw, zorder=2, solid_capstyle="round")
        ax.scatter([0, 1], [a, b], s=70, color=color, edgecolor=BG, linewidth=2, zorder=3)
    # Labels, nudged apart where ranks collide
    for side, season, ha, dx in [(0, "2025-26", "right", -0.04), (1, "2026-27", "left", 0.04)]:
        items = sorted(((ranks[season][lbl], lbl) for lbl, _, _ in metrics))
        placed = []
        for r, lbl in items:
            y = max(r, placed[-1] + 1.15) if placed else r
            placed.append(y)
            text = f"{lbl}  {r}" if side == 0 else f"{r}  {lbl}"
            ax.text(side + dx, y, text, ha=ha, va="center", fontsize=11, color=INK)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(31, -1)
    ax.set_xticks([])
    ax.set_yticks([])
    for x, t in [(0, "2025-26"), (1, "2026-27")]:
        ax.text(x, -1.6, t, ha="center", va="bottom", fontsize=13, fontweight="bold", color=INK)
    save(fig, "knicks_rank_changes.png")


if __name__ == "__main__":
    lineups, opp_strength, matchups = load_all()
    chart_net_rating(lineups)
    chart_four_factors(lineups)
    chart_starters_playoffs(lineups)
    chart_matchup_difficulty(matchups)
    chart_opponent_strength(opp_strength)
    chart_rank_changes()
