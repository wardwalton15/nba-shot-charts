"""
NBA teams — 2026-27 10-0 scoring runs made vs. allowed, from play-by-play.

Produces one PNG file:
  scoring_runs_2026-27.png  — runs made vs. allowed per game, league-average quadrants

Run from the repo root:
    .venv/bin/python examples/scoring_runs_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_scoring_runs_chart

team_scoring_runs_chart(
    season="2026-27",
    min_run=10,
    credit="WARD WALTON",
    refresh=True,  # season in progress — pick up new games
    save_path="scoring_runs_2026-27.png",
)
print("Saved scoring_runs_2026-27.png")
