"""
NBA — 2026-27 leading scorers by court zone to date.

Produces one PNG file:
  zone_leaders_2026-27.png  — half-court split into 11 zones, headshot of the player
                              with the most made field goals in each, plus a leaderboard

Run from the repo root:
    .venv/bin/python examples/zone_leaders_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import zone_leaders_chart

zone_leaders_chart(
    season="2026-27",
    credit="WARD WALTON",
    refresh=True,  # season in progress — always pull the latest games
    save_path="zone_leaders_2026-27.png",
)
print("Saved zone_leaders_2026-27.png")
