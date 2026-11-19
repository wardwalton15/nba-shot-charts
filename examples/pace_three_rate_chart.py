"""
NBA teams — 2026-27 pace vs. three-point attempt rate to date.

Produces one PNG file:
  pace_three_rate_2026-27.png  — every team's pace vs. 3PA/FGA, league-average quadrants

Run from the repo root:
    .venv/bin/python examples/pace_three_rate_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_pace_three_rate_chart

team_pace_three_rate_chart(
    season="2026-27",
    credit="WARD WALTON",
    refresh=True,  # season in progress — always pull the latest games
    save_path="pace_three_rate_2026-27.png",
)
print("Saved pace_three_rate_2026-27.png")
