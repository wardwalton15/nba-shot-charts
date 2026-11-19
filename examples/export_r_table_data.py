"""
Export data for the R/gt tables in r/:
  - r/data/pnr_ballhandler_<season>.csv   Synergy P&R ballhandler totals per player
  - r/data/assist_pairs_<season>.csv      assister -> scorer counts
  - r/data/on_off_<season>.csv            team net rating with each player on / off court,
                                          plus an IS_ROOKIE flag
  - r/data/dribbles_7plus_<season>.csv    shooting on 7+ dribble FGA, with share of total FGA
  - r/data/possessions_<season>.csv       touches and per-touch dribbles / seconds / points
  - r/data/usage_change_<season>.csv      usage rate this season vs. last, one row per player
  - r/data/rim_defense_<season>.csv       defended FG% on shots within 6 ft, per closest defender
  - r/data/matchup_defense_<season>.csv   opponent FGM/FGA and 3PM/3PA in tracked matchups, per defender
  - r/data/two_man_<season>.csv           net rating with each two-man pair on the court together
  - r/data/isolation_<season>.csv         Synergy isolation totals per player
  - r/data/clutch_<season>.csv            box-score totals in clutch time (last 5 min, within 5 pts)
  - r/data/wide_open_<season>.csv         shooting with no defender within 6 ft, plus all-shot 3PM/3PA
  - r/data/hustle_<season>.csv            hustle totals (deflections etc.) joined with steals

Run from repo root (refreshes the in-progress season):
    .venv/bin/python examples/export_r_table_data.py
    .venv/bin/python examples/export_r_table_data.py --season 2025-26 --no-refresh
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_api.stats.endpoints import LeagueDashPlayerStats

from nba_shot_charts.data.fetcher import (
    _sleep_and_fetch, get_assist_pairs, get_clutch_stats, get_dribble_shooting, get_hustle_stats,
    get_play_type_stats, get_player_on_off, get_matchup_defense, get_player_scoring,
    get_possession_tracking, get_rim_defense, get_two_man_lineups, get_wide_open_shooting,
)

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

    on_off = get_player_on_off(args.season, args.season_type, refresh=refresh)
    rookies = _sleep_and_fetch(
        LeagueDashPlayerStats,
        season=args.season,
        season_type_all_star=args.season_type,
        player_experience_nullable="Rookie",
    ).get_data_frames()[0]["PLAYER_ID"]
    on_off["IS_ROOKIE"] = on_off["PLAYER_ID"].isin(rookies).astype(int)
    on_off_path = OUT_DIR / f"on_off_{args.season}.csv"
    on_off.sort_values("NET_DIFF", ascending=False).to_csv(on_off_path, index=False)
    print(f"Wrote {on_off_path} ({len(on_off)} player-team rows, {on_off['IS_ROOKIE'].sum()} rookie)")

    dribbles = get_dribble_shooting("7+ Dribbles", args.season, args.season_type, refresh=refresh)
    dribbles_path = OUT_DIR / f"dribbles_7plus_{args.season}.csv"
    dribbles.sort_values("FGA_FREQUENCY", ascending=False).to_csv(dribbles_path, index=False)
    print(f"Wrote {dribbles_path} ({len(dribbles)} players)")

    poss = get_possession_tracking(args.season, args.season_type, refresh=refresh)
    poss_path = OUT_DIR / f"possessions_{args.season}.csv"
    poss.sort_values("AVG_DRIB_PER_TOUCH", ascending=False).to_csv(poss_path, index=False)
    print(f"Wrote {poss_path} ({len(poss)} players)")

    start = int(args.season[:4]) - 1
    prev_season = f"{start}-{str(start + 1)[2:]}"
    usage_cols = ["PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION", "GP", "MIN", "USG_PCT"]
    cur = get_player_scoring(args.season, args.season_type, refresh=refresh)[usage_cols]
    # Last season is final, so the cache never needs refreshing
    prev = get_player_scoring(prev_season, args.season_type)[usage_cols]
    usage = cur.merge(prev.drop(columns="PLAYER_NAME"), on="PLAYER_ID", suffixes=("", "_PREV"))
    usage["USG_DIFF"] = usage["USG_PCT"] - usage["USG_PCT_PREV"]
    usage_path = OUT_DIR / f"usage_change_{args.season}.csv"
    usage.sort_values("USG_DIFF", ascending=False).to_csv(usage_path, index=False)
    print(f"Wrote {usage_path} ({len(usage)} players in both {prev_season} and {args.season})")

    rim = get_rim_defense(args.season, args.season_type, refresh=refresh)
    rim_path = OUT_DIR / f"rim_defense_{args.season}.csv"
    rim.sort_values("D_FG_PCT").to_csv(rim_path, index=False)
    print(f"Wrote {rim_path} ({len(rim)} players)")

    # Matchup data has no team column, so take it from the player scoring table
    matchups = get_matchup_defense(args.season, args.season_type, refresh=refresh)
    teams = cur[["PLAYER_ID", "TEAM_ID", "TEAM_ABBREVIATION"]]
    matchup_def = matchups.merge(teams, on="PLAYER_ID", how="left")
    matchup_path = OUT_DIR / f"matchup_defense_{args.season}.csv"
    matchup_def.sort_values("MATCHUP_FG_PCT").to_csv(matchup_path, index=False)
    print(f"Wrote {matchup_path} ({len(matchup_def)} players, {matchup_def['TEAM_ID'].isna().sum()} without a team)")

    # GROUP_NAME abbreviates first names ("D. Fox"), so take full names from the scoring table
    two_man = get_two_man_lineups(args.season, args.season_type, refresh=refresh)
    names = cur.set_index("PLAYER_ID")["PLAYER_NAME"]
    two_man["PLAYER1_NAME"] = two_man["PLAYER1_ID"].map(names)
    two_man["PLAYER2_NAME"] = two_man["PLAYER2_ID"].map(names)
    two_man_cols = ["TEAM_ID", "TEAM_ABBREVIATION", "PLAYER1_ID", "PLAYER1_NAME", "PLAYER2_ID", "PLAYER2_NAME",
                    "GP", "W", "L", "MIN", "POSS", "OFF_RATING", "DEF_RATING", "NET_RATING"]
    two_man_path = OUT_DIR / f"two_man_{args.season}.csv"
    two_man[two_man_cols].sort_values("NET_RATING", ascending=False).to_csv(two_man_path, index=False)
    print(f"Wrote {two_man_path} ({len(two_man)} pairs, "
          f"{two_man[['PLAYER1_NAME', 'PLAYER2_NAME']].isna().any(axis=1).sum()} with a missing name)")


    iso = get_play_type_stats("Isolation", args.season, args.season_type, refresh=refresh)
    iso_path = OUT_DIR / f"isolation_{args.season}.csv"
    iso.sort_values("PPP", ascending=False).to_csv(iso_path, index=False)
    print(f"Wrote {iso_path} ({len(iso)} players)")

    clutch = get_clutch_stats(args.season, args.season_type, refresh=refresh)
    clutch_path = OUT_DIR / f"clutch_{args.season}.csv"
    clutch.sort_values("PTS", ascending=False).to_csv(clutch_path, index=False)
    print(f"Wrote {clutch_path} ({len(clutch)} players)")

    wide_open = get_wide_open_shooting(args.season, args.season_type, refresh=refresh)
    wide_open_path = OUT_DIR / f"wide_open_{args.season}.csv"
    wide_open.sort_values("FG3_PCT", ascending=False).to_csv(wide_open_path, index=False)
    print(f"Wrote {wide_open_path} ({len(wide_open)} players)")

    # Hustle data has no steals, so take them from the player scoring table
    hustle = get_hustle_stats(args.season, args.season_type, refresh=refresh)
    hustle = hustle.merge(cur[["PLAYER_ID", "STL"]], on="PLAYER_ID", how="left")
    hustle_path = OUT_DIR / f"hustle_{args.season}.csv"
    hustle.sort_values("DEFLECTIONS", ascending=False).to_csv(hustle_path, index=False)
    print(f"Wrote {hustle_path} ({len(hustle)} players, {hustle['STL'].isna().sum()} without steals)")


if __name__ == "__main__":
    main()
