"""
Jalen Brunson shot chart — 2026 Playoffs.
Produces two files: a scatter chart and a hexbin chart.

Run from the repo root:
    python examples/player_shot_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import player_shot_chart

player_shot_chart(
    player_name="Jalen Brunson",
    season="2025-26",
    season_type="Playoffs",
    chart_type="scatter",
    color_by="made",
    save_path="brunson_playoffs_scatter.png",
)
print("Saved brunson_playoffs_scatter.png")

player_shot_chart(
    player_name="Jalen Brunson",
    season="2025-26",
    season_type="Playoffs",
    chart_type="hexbin",
    save_path="brunson_playoffs_hexbin.png",
)
print("Saved brunson_playoffs_hexbin.png")
