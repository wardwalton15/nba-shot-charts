"""
New York Knicks — 2026-27 three-point shooting to date.

Produces one PNG file:
  knicks_3pt_2026-27.png  — every 3PA (made/missed), zones shaded by 3P% vs. league average

Run from the repo root:
    .venv/bin/python examples/knicks_three_point_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_three_point_chart

team_three_point_chart(
    team_name="Knicks",
    season="2026-27",
    compare_season="2025-26",
    refresh=True,  # season in progress — always pull the latest games
    save_path="knicks_3pt_2026-27.png",
)
print("Saved knicks_3pt_2026-27.png")
