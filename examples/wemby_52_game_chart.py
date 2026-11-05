"""
Victor Wembanyama's 52-point game vs. Dallas, Nov 4, 2026, as a vertical shot chart for TikTok.

Produces one PNG file (1080x1920):
  wemby_52_dal_2026-11-04.png

Run from the repo root:
    .venv/bin/python examples/wemby_52_game_chart.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from nba_shot_charts import player_game_shot_chart

player_game_shot_chart(
    player_name="Victor Wembanyama",
    game_date="2026-11-04",
    season="2026-27",
    credit="WARD WALTON",
    save_path="wemby_52_dal_2026-11-04.png",
)
print("Saved wemby_52_dal_2026-11-04.png")
