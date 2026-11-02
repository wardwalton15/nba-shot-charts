"""
NBA scorers — 2026-27 usage rate vs. true shooting % to date.

Produces one PNG file:
  volume_efficiency_2026-27.png  — every player with 75+ FGA, headshots on the outliers

Run from the repo root:
    .venv/bin/python examples/volume_efficiency_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import scorer_volume_efficiency_chart

scorer_volume_efficiency_chart(
    season="2026-27",
    min_fga=75,
    credit="WARD WALTON",
    refresh=True,  # season in progress — always pull the latest games
    save_path="volume_efficiency_2026-27.png",
)
print("Saved volume_efficiency_2026-27.png")
