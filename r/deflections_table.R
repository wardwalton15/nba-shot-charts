# The league's pickpockets: most deflections per game (NBA hustle stats).
#
# Run from repo root after exporting the data:
#   .venv/bin/python examples/export_r_table_data.py
#   Rscript r/deflections_table.R              # defaults: 2026-27, min 10 GP, min 20 MPG, top 10
#   Rscript r/deflections_table.R 2026-27 15 24 15

source("r/gt_helpers.R")

args <- commandArgs(trailingOnly = TRUE)
season <- if (length(args) >= 1) args[1] else "2026-27"
min_gp <- if (length(args) >= 2) as.integer(args[2]) else 10L
min_mpg <- if (length(args) >= 3) as.numeric(args[3]) else 20
top_n <- if (length(args) >= 4) as.integer(args[4]) else 10L

path <- sprintf("r/data/hustle_%s.csv", season)
hustle <- read.csv(path) |>
  filter(G >= min_gp, MIN / G >= min_mpg) |>
  mutate(DPG = DEFLECTIONS / G)
league_dpg <- median(hustle$DPG)

top <- hustle |>
  arrange(desc(DPG), desc(DEFLECTIONS)) |>
  slice_head(n = top_n) |>
  mutate(
    rank = row_number(),
    player = player_cell(PLAYER_ID, PLAYER_NAME),
    team = logo_cell(TEAM_ID),
    MPG = MIN / G,
    SPG = STL / G,
    D36 = 36 * DEFLECTIONS / MIN
  ) |>
  select(rank, player, team, G, MPG, DEFLECTIONS, SPG, D36, DPG)

defl_tbl <- top |>
  gt() |>
  html_cols(c(player, team)) |>
  cols_label(rank = "", player = "Player", team = "Team", G = "GP", MPG = "MPG",
             DEFLECTIONS = "Deflections", SPG = "STL/G", D36 = "Defl/36", DPG = "Defl/G") |>
  fmt_number(c(MPG, SPG, D36, DPG), decimals = 1) |>
  data_color(DPG, palette = c("#F1F5F9", "#6B46C1"),
             domain = c(league_dpg, max(top$DPG))) |>
  tab_style(cell_text(weight = "bold", size = px(18)), cells_body(DPG)) |>
  tab_style(cell_text(color = SLATE), cells_body(c(MPG, SPG, D36))) |>
  tab_style(cell_text(color = "#94A3B8"), cells_body(rank)) |>
  tab_footnote(sprintf("Median qualified player: %.1f.", league_dpg), cells_column_labels(DPG)) |>
  theme_nba_table(
    "The League's Pickpockets",
    sprintf("Deflections per game · %s regular season · min. %d GP and %g MPG (%d players qualify)",
            season, min_gp, min_mpg, nrow(hustle)),
    paste0("Data: NBA.com hustle stats, as of ", data_as_of(path), ". ",
           "A deflection is any time a defender gets a hand on a pass or dribble, whether or not it becomes a steal.")
  )

save_table(defl_tbl, sprintf("deflections_%s", season))
