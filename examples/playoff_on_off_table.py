"""
2026 Playoffs — Net Rating On/Off Differential Table
Minimum 100 on-court playoff minutes.

Run from repo root:
    .venv/bin/python examples/playoff_on_off_table.py
    .venv/bin/python examples/playoff_on_off_table.py --csv out.csv
    .venv/bin/python examples/playoff_on_off_table.py --no-html
    .venv/bin/python examples/playoff_on_off_table.py --min-min 50
"""
import argparse
import time

import pandas as pd
import plotly.graph_objects as go
from nba_api.stats.endpoints import LeagueGameFinder, TeamPlayerOnOffSummary
from nba_api.stats.static import teams as nba_teams

SEASON = "2025-26"
SLEEP = 0.6
_DEFAULT_SEASON_TYPE = "Playoffs"

_DISPLAY_COLS = [
    "RANK", "VS_PLAYER_NAME", "TEAM_ABBREVIATION", "GP",
    "MIN_ON", "NET_ON", "NET_OFF", "NET_DIFF",
]
_HEADERS = ["#", "Player", "Team", "GP", "MIN (On)", "Net Rtg (On)", "Net Rtg (Off)", "Net Diff"]
_HTML_HEADERS = ["#", "PLAYER", "TEAM", "GP", "MIN ON", "ON NET RTG", "OFF NET RTG", "NET DIFF"]

# Subtle team-tinted row backgrounds
_TEAM_PALETTE = {
    "ATL": "#FDF3F3", "BOS": "#F2FAF3", "BKN": "#F5F5F5", "CHA": "#EFF7FD",
    "CHI": "#FDF0F2", "CLE": "#FDF5ED", "DAL": "#EFF7FD", "DEN": "#FDFAF0",
    "DET": "#FDF0F2", "GSW": "#FDFAF0", "HOU": "#FDF0F2", "IND": "#FDF5ED",
    "LAC": "#FDF0F2", "LAL": "#FAF3FD", "MEM": "#EFF7FD", "MIA": "#FDF0F2",
    "MIL": "#F2FAF3", "MIN": "#EFF7FD", "NOP": "#F3F4FD", "NYK": "#FDF5ED",
    "OKC": "#EEF5FF", "ORL": "#EFF7FD", "PHI": "#EFF7FD", "PHX": "#FDF5ED",
    "POR": "#FDF0F2", "SAC": "#FAF3FD", "SAS": "#F4F4F6", "TOR": "#FDF0F2",
    "UTA": "#EFF7FD", "WAS": "#FDF0F2",
}


def resolve_team_id(abbr: str) -> int:
    lookup = {t["abbreviation"].upper(): t["id"] for t in nba_teams.get_teams()}
    tid = lookup.get(abbr.upper())
    if tid is None:
        raise ValueError(f"Unknown team abbreviation '{abbr}'")
    return tid


def find_series_dates(abbr1: str, abbr2: str, season_type: str) -> tuple[str, str, list[int]]:
    """Return (date_from, date_to, [team_id1, team_id2]) for the series between two teams."""
    t1_id = resolve_team_id(abbr1)
    t2_id = resolve_team_id(abbr2)
    time.sleep(SLEEP)
    result = LeagueGameFinder(
        team_id_nullable=t1_id,
        vs_team_id_nullable=t2_id,
        season_nullable=SEASON,
        season_type_nullable=season_type,
        league_id_nullable="00",
    )
    df = result.get_data_frames()[0]
    if df.empty:
        raise ValueError(f"No {season_type} games found between {abbr1} and {abbr2} in {SEASON}")
    dates = pd.to_datetime(df["GAME_DATE"]).sort_values()
    date_from = dates.iloc[0].strftime("%Y-%m-%d")
    date_to = dates.iloc[-1].strftime("%Y-%m-%d")
    print(f"  Found {len(df)} games: {date_from} → {date_to}")
    return date_from, date_to, [t1_id, t2_id]


def get_playoff_team_ids(season_type: str) -> list[int]:
    print(f"Fetching {SEASON} {season_type} team IDs...")
    time.sleep(SLEEP)
    result = LeagueGameFinder(
        season_nullable=SEASON,
        season_type_nullable=season_type,
        league_id_nullable="00",
    )
    df = result.get_data_frames()[0]
    team_ids = df["TEAM_ID"].drop_duplicates().tolist()
    print(f"  Found {len(team_ids)} playoff teams.")
    return team_ids


def fetch_on_off_data(
    team_ids: list[int],
    season_type: str,
    date_from: str = "",
    date_to: str = "",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    on_frames, off_frames = [], []
    for i, team_id in enumerate(team_ids):
        print(f"  [{i + 1}/{len(team_ids)}] Fetching team {team_id}...")
        time.sleep(SLEEP)
        try:
            result = TeamPlayerOnOffSummary(
                team_id=team_id,
                season=SEASON,
                season_type_all_star=season_type,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                timeout=60,
            )
        except Exception:
            time.sleep(5)
            result = TeamPlayerOnOffSummary(
                team_id=team_id,
                season=SEASON,
                season_type_all_star=season_type,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                timeout=60,
            )
        on_df = result.players_on_court_team_player_on_off_summary.get_data_frame()
        off_df = result.players_off_court_team_player_on_off_summary.get_data_frame()
        on_df["TEAM_ID_SRC"] = team_id
        off_df["TEAM_ID_SRC"] = team_id
        on_frames.append(on_df)
        off_frames.append(off_df)
    return pd.concat(on_frames, ignore_index=True), pd.concat(off_frames, ignore_index=True)


def build_table(all_on: pd.DataFrame, all_off: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    on_slim = (
        all_on[["VS_PLAYER_ID", "VS_PLAYER_NAME", "TEAM_ABBREVIATION", "GP",
                "MIN", "NET_RATING", "TEAM_ID_SRC"]]
        .rename(columns={"MIN": "MIN_ON", "NET_RATING": "NET_ON"})
    )
    off_slim = (
        all_off[["VS_PLAYER_ID", "MIN", "NET_RATING", "TEAM_ID_SRC"]]
        .rename(columns={"MIN": "MIN_OFF", "NET_RATING": "NET_OFF"})
    )

    merged = on_slim.merge(off_slim, on=["VS_PLAYER_ID", "TEAM_ID_SRC"])
    merged = merged.dropna(subset=["NET_ON", "NET_OFF"])

    # For traded players, keep the team with the most on-court minutes
    merged = (
        merged
        .sort_values("MIN_ON", ascending=False)
        .drop_duplicates(subset=["VS_PLAYER_ID"])
        .reset_index(drop=True)
    )

    df = merged[merged["MIN_ON"] >= min_minutes].copy()
    df["NET_DIFF"] = df["NET_ON"] - df["NET_OFF"]
    df = df.sort_values("NET_DIFF", ascending=False).reset_index(drop=True)
    df.insert(0, "RANK", range(1, len(df) + 1))
    return df


def print_table(df: pd.DataFrame, min_minutes: int) -> None:
    out = df[_DISPLAY_COLS].copy()
    out.columns = _HEADERS
    print("\n" + out.to_string(index=False, float_format="{:.1f}".format))
    print(f"\n{len(df)} players with >= {min_minutes} on-court playoff minutes")


def save_csv(df: pd.DataFrame, path: str) -> None:
    df[_DISPLAY_COLS].to_csv(path, index=False, float_format="%.1f")
    print(f"Saved CSV → {path}")


def _fmt_name(name: str) -> str:
    """'Last, First' → 'First Last'"""
    if ", " in name:
        last, first = name.split(", ", 1)
        return f"{first} {last}"
    return name


def save_html(
    df: pd.DataFrame,
    path: str,
    title_label: str = "Playoffs",
    min_minutes: int = 100,
    season_type: str = "Playoffs",
) -> None:
    n = len(df)
    teams = df["TEAM_ABBREVIATION"].tolist()
    diff_vals = df["NET_DIFF"].tolist()

    base_colors  = [_TEAM_PALETTE.get(t, "#F8F9FA") for t in teams]
    rank_colors  = ["#EDEDF0"] * n
    diff_bg      = ["#C6F6D5" if v > 0 else "#FED7D7" for v in diff_vals]
    diff_fg      = ["#1A5C35" if v > 0 else "#8B1515" for v in diff_vals]
    default_fg   = ["#111827"] * n

    player_names = [_fmt_name(name) for name in df["VS_PLAYER_NAME"]]
    net_diff_str = [f"<b>{'+' if x >= 0 else ''}{x:.1f}</b>" for x in diff_vals]

    col_data    = [df["RANK"], player_names, df["TEAM_ABBREVIATION"], df["GP"],
                   df["MIN_ON"], df["NET_ON"], df["NET_OFF"], net_diff_str]
    col_formats = [None, None, None, None, ".0f", ".1f", ".1f", None]
    col_align   = ["center", "left", "center", "center", "center", "center", "center", "center"]
    fill_colors = [rank_colors, base_colors, base_colors, base_colors,
                   base_colors, base_colors, base_colors, diff_bg]
    font_colors = [["#888"] * n, default_fg, default_fg, default_fg,
                   default_fg, default_fg, default_fg, diff_fg]

    subtitle = f"Net Rating On/Off Differential  ·  2025-26 {season_type}  ·  Min. {min_minutes} on-court minutes"

    fig = go.Figure(data=[go.Table(
        columnwidth=[28, 170, 44, 28, 58, 82, 82, 72],
        header=dict(
            values=[f"<b>{h}</b>" for h in _HTML_HEADERS],
            fill_color="#0D1B2A",
            font=dict(color="white", size=11, family="Helvetica Neue, Arial, sans-serif"),
            align=["center", "left", "center", "center", "center", "center", "center", "center"],
            height=38,
            line=dict(color="#0D1B2A", width=0),
        ),
        cells=dict(
            values=col_data,
            fill_color=fill_colors,
            format=col_formats,
            align=col_align,
            font=dict(size=12, family="Helvetica Neue, Arial, sans-serif", color=font_colors),
            height=30,
            line=dict(color="#E2E8F0", width=0.5),
        ),
    )])

    fig.update_layout(
        title=dict(
            text=f"<b>{title_label}</b><br><sup><span style='color:#64748B'>{subtitle}</span></sup>",
            font=dict(size=22, color="#0D1B2A", family="Helvetica Neue, Arial, sans-serif"),
            x=0.5,
            xanchor="center",
            y=0.97,
            yanchor="top",
        ),
        margin=dict(l=24, r=24, t=80, b=36),
        paper_bgcolor="white",
        width=920,
        height=38 + 30 * n + 80 + 36,  # exact fit — no Plotly internal scroll
    )
    fig.add_annotation(
        text="Source: NBA Stats API",
        xref="paper", yref="paper",
        x=1.0, y=-0.03,
        showarrow=False,
        font=dict(size=10, color="#94A3B8", family="Helvetica Neue, Arial, sans-serif"),
        xanchor="right",
    )

    # Scale the figure to fit the viewport height if needed — no page scroll, no clipping
    figure_h = 38 + 30 * n + 80 + 36
    post_script = f"""
(function() {{
  document.body.style.margin = '0';
  document.body.style.background = 'white';
  var fig = document.querySelector('.plotly-graph-div');
  var avail = window.innerHeight - 8;
  var need = {figure_h};
  if (need > avail) {{
    var s = avail / need;
    fig.style.transform = 'scale(' + s + ')';
    fig.style.transformOrigin = 'top left';
    fig.style.marginBottom = '-' + Math.ceil(need * (1 - s)) + 'px';
  }}
  document.body.style.overflow = 'hidden';
}})();
"""

    fig.write_html(path, include_plotlyjs="cdn", post_script=post_script)
    print(f"Saved HTML → {path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="2026 Playoffs on/off net rating differential table")
    p.add_argument("--season-type", default=_DEFAULT_SEASON_TYPE,
                   help="Season type: 'Playoffs' or 'Regular Season' (default: Playoffs)")
    p.add_argument("--series", nargs=2, metavar=("TEAM1", "TEAM2"),
                   help="Filter to a specific series, e.g. --series SAS OKC")
    p.add_argument("--html", metavar="FILE", default=None,
                   help="HTML output path (auto-named by default)")
    p.add_argument("--no-html", action="store_true", help="Skip HTML output")
    p.add_argument("--csv", metavar="FILE", help="Also save as CSV")
    p.add_argument("--min-min", type=int, default=None,
                   help="Minimum on-court minutes (default: 100, or 0 for --series)")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    date_from = date_to = ""
    if args.series:
        abbr1, abbr2 = args.series
        print(f"Finding {SEASON} {args.season_type} series: {abbr1} vs {abbr2}...")
        date_from, date_to, team_ids = find_series_dates(abbr1, abbr2, args.season_type)
        title_label = f"{abbr1} vs {abbr2} series"
        default_html = f"{'_'.join(args.series).lower()}_series_on_off_table.html"
        min_minutes = args.min_min if args.min_min is not None else 0
    else:
        team_ids = get_playoff_team_ids(args.season_type)
        title_label = f"2025-26 {args.season_type}"
        default_html = f"{args.season_type.lower().replace(' ', '_')}_on_off_table.html"
        min_minutes = args.min_min if args.min_min is not None else 100

    html_path = args.html or default_html

    print("Fetching on/off data for each team...")
    all_on, all_off = fetch_on_off_data(team_ids, args.season_type, date_from, date_to)

    df = build_table(all_on, all_off, min_minutes)
    print_table(df, min_minutes)

    if args.csv:
        save_csv(df, args.csv)

    if not args.no_html:
        save_html(df, html_path, title_label, min_minutes, args.season_type)


if __name__ == "__main__":
    main()
