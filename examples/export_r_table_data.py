"""
Export data for the R/gt tables in r/:
  - r/data/pnr_ballhandler_<season>.csv   Synergy P&R ballhandler totals per player
  - r/data/assist_pairs_<season>.csv      assister -> scorer counts

Run from repo root (refreshes the in-progress season):
    .venv/bin/python examples/export_r_table_data.py
    .venv/bin/python examples/export_r_table_data.py --season 2025-26 --no-refresh
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_api.stats.endpoints import LeagueDashPlayerStats

from nba_shot_charts.data.fetcher import _sleep_and_fetch, get_assist_pairs, get_play_type_stats

OUT_DIR = Path(__file__).parent.parent / "r" / "data"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2026-27")
    parser.add_argument("--season-type", default="Regular Season")
    parser.add_argument("--no-refresh", action="store_true")
    args = parser.parse_args()
    refresh = not args.no_refresh
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pnr = get_play_type_stats("PRBallHandler", args.season, args.season_type, refresh=refresh)
    pnr_path = OUT_DIR / f"pnr_ballhandler_{args.season}.csv"
    pnr.to_csv(pnr_path, index=False)
    print(f"Wrote {pnr_path} ({len(pnr)} players)")

    pairs = get_assist_pairs(args.season, args.season_type, refresh=refresh)
    totals = _sleep_and_fetch(
        LeagueDashPlayerStats,
        season=args.season,
        season_type_all_star=args.season_type,
        per_mode_detailed="Totals",
    ).get_data_frames()[0][["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION", "AST"]]

    # Sanity check: PBP-derived assists vs. official box score totals
    pbp_ast = pairs.groupby("ASSISTER_ID").size()
    official = totals.set_index("PLAYER_ID")["AST"]
    off_by = (pbp_ast.reindex(official.index, fill_value=0) - official).abs()
    print(f"Assist check: {pairs['ASSISTER_ID'].isna().sum()} unresolved, "
          f"{(off_by > 0).sum()} players differ from box score (max diff {off_by.max()})")

    agg = (
        pairs.dropna(subset=["ASSISTER_ID"])
        .groupby(["TEAM_ID", "ASSISTER_ID", "SCORER_ID"])
        .agg(AST=("SHOT_VALUE", "size"), PTS=("SHOT_VALUE", "sum"),
             AST_3PM=("SHOT_VALUE", lambda v: (v == 3).sum()))
        .reset_index()
    )
    names = totals.set_index("PLAYER_ID")["PLAYER_NAME"]
    agg["ASSISTER_NAME"] = agg["ASSISTER_ID"].map(names)
    agg["SCORER_NAME"] = agg["SCORER_ID"].map(names)
    agg["ASSISTER_TOTAL_AST"] = agg["ASSISTER_ID"].map(official)
    agg["TEAM_ABBREVIATION"] = agg["TEAM_ID"].map(totals.drop_duplicates("TEAM_ID").set_index("TEAM_ID")["TEAM_ABBREVIATION"])

    pairs_path = OUT_DIR / f"assist_pairs_{args.season}.csv"
    agg.sort_values("AST", ascending=False).to_csv(pairs_path, index=False)
    print(f"Wrote {pairs_path} ({len(agg)} duos)")


if __name__ == "__main__":
    main()
