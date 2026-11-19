# Best wide-open shooters: 3P% on threes with no defender within 6 ft (NBA player tracking).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/wide_open_threes_table.R              # defaults: 2026-27, min 35 wide-open 3PA, top 10
#   Rscript r/wide_open_threes_table.R 2026-27 50 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_3pa <- if (length(args) >= 2) as.integer(args[2]) else 35L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/wide_open_%s.csv", season)
all_players <- read.csv(path)
league_wo <- with(all_players, sum(FG3M) / sum(FG3A))
wo <- all_players |>
  filter(FG3A >= min_3pa) |>
  mutate(WO_PCT = FG3M / FG3A)

top <- wo |>
  arrange(desc(WO_PCT), desc(FG3A)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    shots = sprintf("%d-%d", as.integer(FG3M), as.integer(FG3A)),
    SHARE = 100 * FG3A / TOTAL_FG3A,
    ALL3 = 100 * TOTAL_FG3M / TOTAL_FG3A,
    WO = 100 * WO_PCT
  ) |>
  select(rank, player, team, GP, shots, SHARE, ALL3, WO)

wo_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", shots = "Open 3PM-3PA",
             SHARE = "Open Share", ALL3 = "All 3P%", WO = "Open 3P%") |>
  fmt_number(c(SHARE, ALL3, WO), decimals = 1) |>
  fmt_percent(SHARE, decimals = 0, scale_values = FALSE) |>
  data_color(WO, palette = c("#F1F5F9", "#2B6CB0"),
             domain = c(100 * league_wo, max(top$WO))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(WO)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(SHARE, ALL3))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Share of the player's 3PA that were wide open.", cells_column_labels(SHARE)) |>
  tab_footnote(sprintf("League-wide on wide-open threes: %.1f%%.", 100 * league_wo),
               cells_column_labels(WO)) |>
  theme_nba_table(
    "Don't Leave Them Open",
    sprintf("3P%% with no defender within 6 ft · %s regular season · min. %d wide-open 3PA (%d players qualify)",
            season, min_3pa, nrow(wo)),
    paste0("Data: NBA.com player tracking, as of ", data_as_of(path), ". ",
           "Distance to the closest defender is measured at the moment of the shot. ",
           "Early-season samples are small and noisy.")
  )

save_table(wo_tbl, sprintf("wide_open_threes_%s", season))
