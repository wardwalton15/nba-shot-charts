# Shared pieces for the gt tables in r/. Source from repo root:
#   source("r/gt_helpers.R")

suppressPackageStartupMessages({
  library(dplyr)
  library(gt)
})

FONT <- c("Helvetica Neue", "Arial", "sans-serif")
NAVY <- "#0D1B2A"
SLATE <- "#64748B"

headshot_url <- function(player_id) {
  sprintf("https://cdn.nba.com/headshots/nba/latest/260x190/%s.png", player_id)
}

logo_url <- function(team_id) {
  sprintf("https://cdn.nba.com/logos/nba/%s/primary/L/logo.svg", team_id)
}

# Headless Chrome (webshot2) can't load the NBA CDN images, so download once to
# cache/images/ and inline them as data URIs — also keeps the HTML self-contained.
IMG_DIR <- "cache/images"

data_uri <- function(url) {
  vapply(url, function(u) {
    dir.create(IMG_DIR, showWarnings = FALSE, recursive = TRUE)
    path <- file.path(IMG_DIR, gsub("[^A-Za-z0-9.]+", "_", sub("^https://cdn.nba.com/", "", u)))
    if (!file.exists(path)) {
      resp <- httr::GET(u, httr::timeout(20))
      if (httr::status_code(resp) != 200) return(u)  # fall back to the remote URL
      writeBin(httr::content(resp, "raw"), path)
    }
    mime <- if (grepl("\\.svg$", path)) "image/svg+xml" else "image/png"
    paste0("data:", mime, ";base64,", jsonlite::base64_enc(readBin(path, "raw", file.size(path))))
  }, character(1), USE.NAMES = FALSE)
}

# Round headshot with the name beside it, as an HTML string for text_transform()
player_cell <- function(player_id, name, size = 44) {
  sprintf(
    paste0(
      '<div style="display:flex;align-items:center;gap:10px;">',
      '<img src="%s" style="width:%dpx;height:%dpx;border-radius:50%%;object-fit:cover;',
      'object-position:top;background:#EEF2F6;border:1px solid #E2E8F0;">',
      '<span style="font-weight:600;">%s</span></div>'
    ),
    data_uri(headshot_url(player_id)), size, size, name
  )
}

logo_cell <- function(team_id, size = 34) {
  sprintf('<img src="%s" style="height:%dpx;width:%dpx;">', data_uri(logo_url(team_id)), size, size)
}

# Renders pre-built HTML strings in the given columns as-is (default formatting escapes them)
html_cols <- function(tbl, columns) {
  fmt(tbl, columns = {{ columns }}, fns = function(x) lapply(x, gt::html))
}

theme_nba_table <- function(tbl, title, subtitle, source_note) {
  tbl |>
    tab_header(title = md(paste0("**", title, "**")), subtitle = subtitle) |>
    tab_source_note(source_note) |>
    opt_table_font(font = FONT) |>
    opt_align_table_header(align = "left") |>
    tab_options(
      table.border.top.style = "hidden",
      heading.title.font.size = px(24),
      heading.subtitle.font.size = px(14),
      heading.padding = px(6),
      column_labels.background.color = NAVY,
      column_labels.font.size = px(12),
      column_labels.font.weight = "bold",
      column_labels.text_transform = "uppercase",
      table_body.hlines.color = "#E2E8F0",
      data_row.padding = px(6),
      source_notes.font.size = px(11),
      table.font.color = "#111827"
    ) |>
    tab_style(cell_text(color = SLATE), cells_title("subtitle")) |>
    tab_style(cell_text(color = "#94A3B8"), cells_source_notes()) |>
    cols_align("center", columns = -any_of(c("player", "assister", "scorer")))
}

# Writes <stem>.html and <stem>.png at the repo root
save_table <- function(tbl, stem) {
  gtsave(tbl, paste0(stem, ".html"))
  gtsave(tbl, paste0(stem, ".png"), expand = 20, zoom = 2)
  message("Wrote ", stem, ".html / .png")
}

data_as_of <- function(path) {
  d <- file.mtime(path)
  paste0(format(d, "%b "), as.integer(format(d, "%d")), format(d, ", %Y"))
}
