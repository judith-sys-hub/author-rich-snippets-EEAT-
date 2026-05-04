# Sub-project 5: Styled Excel Review File — Design Spec

**Goal:** Replace the plain `author_review.csv` with a formatted `author_review.xlsx` that editors can open directly in Google Sheets — with readable bio text, color-coded status, a beats column, and a live progress summary row.

**Date:** 2026-05-04

---

## Problem

The current CSV has three usability issues reported by editors:
- Bio text is unreadable in a spreadsheet cell without manual row-height adjustment
- No progress overview (how many approved / flagged / pending)
- Five separate beat columns (`beat_1`…`beat_5`) look like database output, not an editorial tool

---

## Decisions

| Question | Decision |
|---|---|
| Format | `.xlsx` (replaces `.csv`) |
| Library | `openpyxl` (new dependency) |
| Beats representation | One column `themen`, semicolon-separated |
| Summary row | Row 1, COUNTIF formulas, updates live as editors type |
| Header row | Row 2, frozen |
| Status input | Data validation dropdown (pending / approved / flagged) |
| Conditional formatting | Column C: green / yellow / red by status value |

---

## Column Structure

| Column | Field | Width | Editable? | Notes |
|---|---|---|---|---|
| A | `slug` | 22 | no | Narrow, light grey font — needed by importer |
| B | `name` | 22 | no | Context only |
| C | `status` | 12 | yes | Dropdown: `pending` / `approved` / `flagged` |
| D | `bio` | 60 | yes | `wrap_text=True`, row height 60pt |
| E | `themen` | 35 | yes | Beats joined with `; ` on export, split on `; ` on import |

---

## Row Structure

- **Row 1 — Summary:** Labels and COUNTIF formulas across columns A–E
  - A1: `"Fortschritt"`
  - B1: `=COUNTA(A3:A{last_row})` — Gesamt (last_row computed from author count at export time)
  - C1: `=COUNTIF(C3:C{last_row},"approved")` — Freigegeben
  - D1: `=COUNTIF(C3:C{last_row},"pending")` — Offen
  - E1: `=COUNTIF(C3:C{last_row},"flagged")` — Markiert
  - Row 1 background: light blue (`#E3F2FD`), bold
- **Row 2 — Headers:** `slug` / `name` / `status` / `bio` / `themen`
  - Background: `#E8EAF6`, bold, frozen (freeze from row 3)
- **Rows 3+ — Data:** One author per row, status pre-filled as `pending`

---

## Formatting Details

**Conditional formatting on column C (status):**
- `"approved"` → green fill `#C8E6C9`, dark green text `#1B5E20`
- `"flagged"` → red fill `#FFCDD2`, dark red text `#B71C1C`
- `"pending"` → yellow fill `#FFF9C4`, dark orange text `#F57F17`

**Data validation on column C:**
- Dropdown list: `pending,approved,flagged`
- Applied to C3:C{last_row}

**Bio column (D):**
- `wrap_text=True`
- Row height: 60pt for data rows
- Column width: 60

**Slug column (A):**
- Font colour: light grey (`#BBBBBB`)
- Column width: 22

---

## Architecture

`review/export.py` gains a new internal function `write_xlsx(rows, xlsx_path)` that handles all openpyxl logic. The existing `build_row()` logic is unchanged — it still produces a dict. `export_authors()` calls `write_xlsx()` instead of the csv write block.

`review/importer.py` gains a new internal function `read_xlsx(xlsx_path)` that reads rows from the xlsx and returns a list of dicts with keys `slug`, `name`, `status`, `bio`, `themen`. The existing `import_authors()` loop is updated to call `parse_beats_from_themen(themen_str)` instead of the old beat-column logic.

`review/__init__.py` removes `BEAT_COLS` and `FIELDNAMES` (no longer needed — xlsx has no fixed column list contract). The file is kept as an empty `__init__.py` to preserve the `review` package structure.

---

## Changed Interfaces

| Function | Before | After |
|---|---|---|
| `export_authors()` | writes `.csv` | writes `.xlsx` |
| `import_authors()` | reads `.csv`, parses `beat_1`…`beat_5` | reads `.xlsx`, parses `themen` split on `; ` |
| `parse_beats()` | reads beat columns from CSV row dict | replaced by `parse_beats_from_themen(s: str) -> list[str]` |

---

## .gitignore

Replace `review/author_review.csv` with `review/author_review.xlsx`.

---

## New / Modified Files

| File | Change |
|---|---|
| `review/export.py` | Add `write_xlsx()`; update `export_authors()` |
| `review/importer.py` | Add `read_xlsx()`; replace `parse_beats()` with `parse_beats_from_themen()`; update `import_authors()` |
| `review/__init__.py` | Remove `BEAT_COLS` and `FIELDNAMES` |
| `requirements.txt` | Add `openpyxl` |
| `.gitignore` | `review/author_review.csv` → `review/author_review.xlsx` |
| `tests/test_review_export.py` | Update to assert `.xlsx` output; add tests for summary row, conditional formatting, data validation |
| `tests/test_review_import.py` | Update to write `.xlsx` fixtures; update `_make_row()` to use `themen` instead of `beat_1`…`beat_5` |

---

## Testing

**`tests/test_review_export.py`:**
- `write_xlsx` produces a file with correct sheet dimensions (rows = authors + 2 header rows)
- Summary row contains COUNTIF formulas (check cell value starts with `=COUNTIF`)
- Header row has correct column names
- Data row has correct values for slug, name, status, bio, themen
- `themen` is semicolon-joined beats
- Authors with no beats have empty `themen` cell
- Conditional formatting rules present on column C
- Data validation present on column C

**`tests/test_review_import.py`:**
- `parse_beats_from_themen("Sport; Fussball; Tennis")` returns `["Sport", "Fussball", "Tennis"]`
- `parse_beats_from_themen("")` returns `[]`
- `parse_beats_from_themen` strips whitespace around each beat
- Approved row with changed bio updates JSON
- Approved row with changed themen updates beats in JSON
- Approved row unchanged does not write files
- Flagged row: no changes, no `update_stage`
- Pending row: silently skipped
- Missing xlsx file raises clear error
