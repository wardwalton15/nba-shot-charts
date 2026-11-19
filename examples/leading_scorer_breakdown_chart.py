"""
NBA teams — 2026-27 leading scorers and where their points come from.

Produces one PNG file:
  leading_scorer_breakdown_2026-27.png  — each team's qualified leading scorer, PPG
                                          split into paint 2s, mid-range 2s, 3s and FTs

Run from the repo root:
    .venv/bin/python examples/leading_scorer_breakdown_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_leading_scorer_breakdown_chart

team_leading_scorer_breakdown_chart(
    season="2026-27",
    credit="WARD WALTON",
    refresh=True,  # season in progress — always pull the latest games
    save_path="leading_scorer_breakdown_2026-27.png",
)
print("Saved leading_scorer_breakdown_2026-27.png")
