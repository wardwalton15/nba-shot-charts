"""
NBA teams — 2026-27 three-point attempt rate vs. 3P% to date.

Produces one PNG file:
  three_rate_2026-27.png  — every team's 3PA/FGA vs. 3P%, league-average quadrants

Run from the repo root:
    .venv/bin/python examples/three_rate_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_three_rate_chart

team_three_rate_chart(
    season="2026-27",
    credit="WARD WALTON",
    refresh=True,  # season in progress — always pull the latest games
    save_path="three_rate_2026-27.png",
)
print("Saved three_rate_2026-27.png")
