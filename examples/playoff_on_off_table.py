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


def save_html(df: pd.DataFrame, path: str, title_label: str = "Playoffs", min_minutes: int = 100) -> None:
    diff_vals = df["NET_DIFF"].tolist()
    diff_colors = [
        "rgba(0,160,0,0.20)" if v > 0 else "rgba(200,0,0,0.20)"
        for v in diff_vals
    ]

    net_diff_str = df["NET_DIFF"].apply(lambda x: f"+{x:.1f}" if x >= 0 else f"{x:.1f}").tolist()
    col_data = [df[c] for c in _DISPLAY_COLS[:-1]] + [net_diff_str]
    col_formats = [None, None, None, None, ".0f", ".1f", ".1f", None]
    col_align = ["center", "left", "center", "center", "center", "center", "center", "center"]
    fill_colors = [["#f8f8f8"] * len(df)] * 7 + [diff_colors]

    fig = go.Figure(data=[go.Table(
        columnwidth=[30, 160, 50, 30, 60, 80, 80, 80],
        header=dict(
            values=_HEADERS,
            fill_color="#1a1a2e",
            font=dict(color="white", size=12),
            align="center",
            height=36,
        ),
        cells=dict(
            values=col_data,
            fill_color=fill_colors,
            format=col_formats,
            align=col_align,
            font=dict(size=12),
            height=32,
        ),
    )])
    fig.update_layout(
        title=dict(
            text=f"{title_label} — Net Rating On/Off Differential (min. {min_minutes} on-court minutes)",
            font=dict(size=16),
        ),
        margin=dict(l=20, r=20, t=60, b=20),
        height=80 + 32 * len(df),
    )
    fig.write_html(path)
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
        save_html(df, html_path, title_label, min_minutes)


if __name__ == "__main__":
    main()
