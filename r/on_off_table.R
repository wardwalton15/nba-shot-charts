# Top players by on/off net rating differential: team net rating with the player
# on the court minus with them off it.
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/on_off_table.R                  # defaults: 2026-27, min 150 minutes, top 10
#   Rscript r/on_off_table.R 2026-27 200 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_min <- if (length(args) >= 2) as.integer(args[2]) else 150L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/on_off_%s.csv", season)
on_off <- read.csv(path) |>
  group_by(PLAYER_ID) |>
  slice_max(MIN_ON, n = 1, with_ties = FALSE) |>  # traded players: team with the most minutes
  ungroup() |>
  filter(MIN_ON >= min_min)

top <- on_off |>
  arrange(desc(NET_DIFF), desc(MIN_ON)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID)
  ) |>
  select(rank, player, team, GP, MIN_ON, NET_RATING_ON, NET_RATING_OFF, NET_DIFF)

signed <- function(x) sprintf("%s%.1f", ifelse(x > 0, "+", ""), x)

on_off_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", MIN_ON = "Min",
             NET_RATING_ON = "Net On", NET_RATING_OFF = "Net Off", NET_DIFF = "On/Off") |>
  fmt_number(MIN_ON, decimals = 0) |>
  fmt(c(NET_RATING_ON, NET_RATING_OFF, NET_DIFF), fns = signed) |>
  data_color(NET_DIFF, palette = c("#F1F5F9", "#2F855A"), domain = c(0, max(top$NET_DIFF))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(NET_DIFF)) |>
  tab_style(cell_text(color = "#2F855A"), cells_body(NET_RATING_ON, rows = NET_RATING_ON > 0)) |>
  tab_style(cell_text(color = "#C53030"), cells_body(NET_RATING_ON, rows = NET_RATING_ON < 0)) |>
  tab_style(cell_text(color = "#2F855A"), cells_body(NET_RATING_OFF, rows = NET_RATING_OFF > 0)) |>
  tab_style(cell_text(color = "#C53030"), cells_body(NET_RATING_OFF, rows = NET_RATING_OFF < 0)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Team net rating with player on court minus with player off court.",
               cells_column_labels(NET_DIFF)) |>
  theme_nba_table(
    "Biggest On/Off Impact",
    sprintf("Net rating on/off differential · %s regular season · min. %d minutes (%d players qualify)",
            season, min_min, nrow(on_off)),
    paste0("Data: NBA.com, as of ", data_as_of(path), ". Net rating = points per 100 possessions, ",
           "scored minus allowed. Early-season samples are small and noisy.")
  )

save_table(on_off_tbl, sprintf("on_off_%s", season))
