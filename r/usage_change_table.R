# Players with the biggest jump in usage rate from last season to this season.
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/usage_change_table.R                # defaults: 2026-27, min 150 MIN both seasons, top 15
#   Rscript r/usage_change_table.R 2026-27 300 20

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_min <- if (length(args) >= 2) as.integer(args[2]) else 150L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 15L

start <- as.integer(substr(season, 1, 4)) - 1L
prev_season <- sprintf("%d-%s", start, substr(start + 1L, 3, 4))

path <- sprintf("r/data/usage_change_%s.csv", season)
usage <- read.csv(path) |>
  filter(MIN >= min_min, MIN_PREV >= min_min) |>
  mutate(across(c(USG_PCT, USG_PCT_PREV, USG_DIFF), \(x) 100 * x))

top <- usage |>
  arrange(desc(USG_DIFF)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    # Highlight a team change since last season
    prev_team = ifelse(TEAM_ID_PREV == TEAM_ID, "", logo_cell(TEAM_ID_PREV, size = 26))
  ) |>
  select(rank, player, prev_team, team, GP, MIN, USG_PCT_PREV, USG_PCT, USG_DIFF)

usage_tbl <- top |>
  gt() |>
  html_cols(c(player, prev_team, team)) |>
  cols_label(rank = "", player = "Player", prev_team = "From", team = "Team",
             USG_PCT_PREV = prev_season, USG_PCT = season, USG_DIFF = "Change") |>
  tab_spanner("Usage Rate", c(USG_PCT_PREV, USG_PCT, USG_DIFF)) |>
  fmt_number(MIN, decimals = 0) |>
  fmt_number(c(USG_PCT_PREV, USG_PCT), decimals = 1) |>
  fmt_number(USG_DIFF, decimals = 1, force_sign = TRUE) |>
  data_color(USG_DIFF, palette = c("#F1F5F9", "#2B6CB0"),
             domain = c(0, max(top$USG_DIFF))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(USG_DIFF)) |>
  tab_style(cell_text(color = SLATE), cells_body(USG_PCT_PREV)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Estimated share of team plays a player uses (FGA, FTA, turnovers) while on the floor.",
               cells_column_spanners("Usage Rate")) |>
  tab_footnote("Logo shown when the player's team changed since last season.",
               cells_column_labels(prev_team)) |>
  tab_footnote("Minutes this season.", cells_column_labels(MIN)) |>
  theme_nba_table(
    "Biggest Usage Rate Increases",
    sprintf("%s vs. %s regular season · min. %d minutes in both seasons (%d players qualify)",
            season, prev_season, min_min, nrow(usage)),
    paste0("Data: NBA.com, as of ", data_as_of(path), ". ",
           "Early-season samples are small and noisy.")
  )

save_table(usage_tbl, sprintf("usage_change_%s", season))
