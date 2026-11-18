# Best two-man pairs by team net rating with both players on the court together.
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/two_man_table.R                 # defaults: 2026-27, min 200 minutes, top 10
#   Rscript r/two_man_table.R 2026-27 300 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_min <- if (length(args) >= 2) as.integer(args[2]) else 200L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/two_man_%s.csv", season)
qual <- read.csv(path) |>
  filter(MIN >= min_min)

top <- qual |>
  arrange(desc(NET_RATING), desc(MIN)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player1 = player_cell(PLAYER1_ID, PLAYER1_NAME),
    plus = "+",
    player2 = player_cell(PLAYER2_ID, PLAYER2_NAME),
    team = logo_cell(TEAM_ID)
  ) |>
  select(rank, player1, plus, player2, team, GP, MIN, OFF_RATING, DEF_RATING, NET_RATING)

signed <- function(x) sprintf("%s%.1f", ifelse(x > 0, "+", ""), x)

tbl <- top |>
  gt() |>
  html_cols(c(player1, plus, player2, team)) |>
  cols_label(rank = "", player1 = "Duo", plus = "", player2 = "", team = "Team", MIN = "Min",
             OFF_RATING = "Off Rtg", DEF_RATING = "Def Rtg", NET_RATING = "Net Rtg") |>
  cols_align("left", columns = c(player1, player2)) |>
  fmt_number(MIN, decimals = 0) |>
  fmt_number(c(OFF_RATING, DEF_RATING), decimals = 1) |>
  fmt(NET_RATING, fns = signed) |>
  data_color(NET_RATING, palette = c("#F1F5F9", "#2F855A"),
             domain = c(0, max(top$NET_RATING))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(NET_RATING)) |>
  tab_style(cell_text(color = "#94A3B8", size = px(18)), cells_body(plus)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(GP, MIN))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Points scored and allowed per 100 possessions with both players on the court.",
               cells_column_labels(c(OFF_RATING, DEF_RATING))) |>
  theme_nba_table(
    "Best Two-Man Duos",
    sprintf("Net rating with both players on the court · %s regular season · min. %d minutes together (%d pairs qualify)",
            season, min_min, nrow(qual)),
    paste0("Data: NBA.com lineups, as of ", data_as_of(path), ". ",
           "Net rating = points per 100 possessions, scored minus allowed. Early-season samples are small and noisy.")
  ) |>
  cols_align("left", columns = c(player1, player2))

save_table(tbl, sprintf("two_man_%s", season))
