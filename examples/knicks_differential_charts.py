"""
New York Knicks — 2025-26 Playoffs vs. Regular Season differential shot charts.

Produces two PNG files:
  knicks_freq_diff.png     — where shot attempt % went up/down in the playoffs
  knicks_eff_diff.png      — where pts/shot attempt went up/down in the playoffs

Run from the repo root:
    .venv/bin/python examples/knicks_differential_charts.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import team_comparison_charts

team_comparison_charts(
    team_name="Knicks",
    season="2025-26",
    freq_save_path="knicks_freq_diff.png",
    efficiency_save_path="knicks_eff_diff.png",
)
print("Saved knicks_freq_diff.png and knicks_eff_diff.png")
