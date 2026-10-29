"""
NBA team tiers — 2026-27 offensive vs. defensive rating to date.

Produces one PNG file:
  team_tiers_2026-27.png  — every team's ORtg vs. DRtg, banded by net-rating tier

Run from the repo root:
    .venv/bin/python examples/team_tiers_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_ratings_chart

team_ratings_chart(
    season="2026-27",
    credit="WARD WALTON",
    refresh=True,  # season in progress — always pull the latest games
    save_path="team_tiers_2026-27.png",
)
print("Saved team_tiers_2026-27.png")
