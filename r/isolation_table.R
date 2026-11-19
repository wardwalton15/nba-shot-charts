# Most efficient isolation scorers: points per isolation possession (Synergy).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/isolation_table.R              # defaults: 2026-27, min 25 iso possessions, top 10
#   Rscript r/isolation_table.R 2026-27 40 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_poss <- if (length(args) >= 2) as.integer(args[2]) else 25L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/isolation_%s.csv", season)
# PPP from the API is rounded, so recompute it from totals
iso <- read.csv(path) |>
  filter(POSS >= min_poss) |>
  mutate(PPP = PTS / POSS)
league_ppp <- with(iso, sum(PTS) / sum(POSS))

top <- iso |>
  arrange(desc(PPP), desc(POSS)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID)
  ) |>
  select(rank, player, team, GP, POSS, PTS, FG_PCT, TOV_POSS_PCT, PPP)

iso_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", POSS = "Iso Poss",
             FG_PCT = "FG%", TOV_POSS_PCT = "TOV%", PPP = "Pts/Poss") |>
  fmt_percent(c(FG_PCT, TOV_POSS_PCT), decimals = 1) |>
  fmt_number(PPP, decimals = 2) |>
  data_color(PPP, palette = c("#F1F5F9", "#2F855A"),
             domain = c(league_ppp, max(top$PPP))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(PPP)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(FG_PCT, TOV_POSS_PCT))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote(sprintf("Points ÷ isolation possessions finished. All qualified players combined: %.2f.", league_ppp),
               cells_column_labels(PPP)) |>
  theme_nba_table(
    "Best Isolation Scorers",
    sprintf("Points per iso possession · %s regular season · min. %d possessions (%d players qualify)",
            season, min_poss, nrow(iso)),
    paste0("Data: NBA.com / Synergy, as of ", data_as_of(path), ". ",
           "Synergy credits a possession to the player who finishes it (shot, shooting foul or turnover). ",
           "Early-season samples are small and noisy.")
  )

save_table(iso_tbl, sprintf("isolation_ppp_%s", season))
