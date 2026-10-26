# P&R ballhandler tables (Synergy play type data):
#   1. Highest PPP          (min. 20 P&R possessions as ballhandler)
#   2. Highest shot rate    (FGA / P&R possessions, same min.)
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/pnr_ballhandler_tables.R            # defaults: 2026-27, min 20, top 10
#   Rscript r/pnr_ballhandler_tables.R 2026-27 25 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_poss <- if (length(args) >= 2) as.integer(args[2]) else 20L
top_n <- if (length(args) >= 3) as.integer(args[3]) else 10L

path <- sprintf("r/data/pnr_ballhandler_%s.csv", season)
pnr <- read.csv(path) |>
  filter(POSS >= min_poss) |>
  mutate(
    SHOT_RATE = FGA / POSS,
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID)
  )

subtitle <- sprintf(
  "P&R ballhandlers, %s regular season · min. %d possessions (%d players qualify)",
  season, min_poss, nrow(pnr)
)
source_note <- paste0(
  "Data: NBA.com / Synergy, as of ", data_as_of(path), ". ",
  "Synergy counts a P&R possession for the ballhandler only when they finish it ",
  "(shot, shooting foul or turnover); passes out of the P&R are excluded."
)

# 1. PPP ----------------------------------------------------------------------
ppp_tbl <- pnr |>
  arrange(desc(PPP), desc(POSS)) |>
  slice_head(n = top_n) |>
  mutate(rank = row_number()) |>
  select(rank, player, team, GP, POSS, PTS, PPP, EFG_PCT, TOV_POSS_PCT) |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", POSS = "Poss",
             EFG_PCT = "eFG%", TOV_POSS_PCT = "TOV%") |>
  fmt_number(PPP, decimals = 2) |>
  fmt_percent(c(EFG_PCT, TOV_POSS_PCT), decimals = 1) |>
  data_color(PPP, palette = c("#F1F5F9", "#2F855A"), domain = range(pnr$PPP)) |>
  tab_style(cell_text(weight = "bold"), cells_body(PPP)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  theme_nba_table("Most Efficient P&R Ballhandlers", paste(subtitle, "· points per possession"), source_note)

save_table(ppp_tbl, sprintf("pnr_ballhandler_ppp_%s", season))

# 2. Shot rate ----------------------------------------------------------------
shot_tbl <- pnr |>
  arrange(desc(SHOT_RATE), desc(POSS)) |>
  slice_head(n = top_n) |>
  mutate(rank = row_number()) |>
  select(rank, player, team, POSS, FGA, SHOT_RATE, SF_POSS_PCT, TOV_POSS_PCT, PPP) |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", POSS = "Poss",
             SHOT_RATE = "Shot %", SF_POSS_PCT = "Fouled %", TOV_POSS_PCT = "TOV%") |>
  fmt_percent(c(SHOT_RATE, SF_POSS_PCT, TOV_POSS_PCT), decimals = 1) |>
  fmt_number(PPP, decimals = 2) |>
  data_color(SHOT_RATE, palette = c("#F1F5F9", "#2B6CB0"), domain = range(pnr$SHOT_RATE)) |>
  tab_style(cell_text(weight = "bold"), cells_body(SHOT_RATE)) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote("Field-goal attempts ÷ P&R possessions finished.", cells_column_labels(SHOT_RATE)) |>
  theme_nba_table("P&R Ballhandlers Who Look for Their Own Shot", subtitle, source_note)

save_table(shot_tbl, sprintf("pnr_ballhandler_shot_rate_%s", season))
