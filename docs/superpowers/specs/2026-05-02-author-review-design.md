# Sub-project 4: Author Review Workflow — Design Spec

**Goal:** A spreadsheet-based workflow that lets Kleine Zeitung editors review, lightly edit, and approve the 231 generated author bios and beats before CMS import.

**Date:** 2026-05-02

---

## Decisions

| Question | Decision |
|---|---|
| Interface | Spreadsheet (CSV/Excel) |
| Editable fields | `bio_generated` and `beats` only |
| Architecture | Two standalone scripts: `review/export.py` + `review/import.py` |
| Re-render on edit | Yes — import auto-regenerates `richsnippet/{slug}.json` for changed authors |
| New pipeline state | `rendered → reviewed` |

---

## Architecture

```
review/
  export.py          — reads DB, writes author_review.csv
  import.py          — reads author_review.csv, updates JSON + richsnippets
  author_review.csv  — the handoff file (gitignored)
```

Two standalone scripts with a human editing step between them. No new dependencies — stdlib only (`csv`, `json`, `pathlib`).

`scraper/state.py` and `scraper/render.py` are reused directly — no changes needed to either.

---

## CSV Format

Each row is one author. Columns:

| Column | Editable? | Notes |
|---|---|---|
| `slug` | no | Primary key — import uses this to find the JSON file |
| `name` | no | For human context only |
| `status` | yes | `pending` (default) / `approved` / `flagged` |
| `bio` | yes | The `bio_generated` text |
| `beat_1` | yes | First beat |
| `beat_2` | yes | Second beat |
| `beat_3` | yes | Third beat |
| `beat_4` | yes | Fourth beat (empty if fewer than 4 beats) |
| `beat_5` | yes | Fifth beat (empty if fewer than 5 beats) |

Beats get individual columns so they are easy to edit in Excel/Google Sheets without delimiter concerns. Empty `beat_*` cells are ignored on import. Up to 5 beats supported; export caps at 5 columns regardless of actual count.

Export always writes `status = pending`. Import processes only `approved` rows; `flagged` and `pending` rows are skipped.

---

## Export Script (`review/export.py`)

Reads all `rendered` authors from the DB, loads each `data/authors/{slug}.json`, writes `review/author_review.csv`.

**CLI:**
```
python review/export.py
```

- Overwrites existing CSV (safe to re-run)
- No arguments needed
- Always reads from `rendered` stage, always writes to `review/author_review.csv`

**Console output:**
```
[export] 231 Autoren exportiert → review/author_review.csv
```

---

## Import Script (`review/import.py`)

Reads `review/author_review.csv` and processes every row where `status == approved`.

**CLI:**
```
python review/import.py
```

**Per approved author:**
1. Load `data/authors/{slug}.json`
2. Collect non-empty `beat_1`…`beat_5` values into a list
3. Compare `bio` and beats against current JSON values
4. If changed: write updated `data/authors/{slug}.json`, re-render `richsnippet/{slug}.json` by calling `render_jsonld()` directly
5. Call `update_stage(slug, "reviewed")`

**Per flagged author:** log the slug, skip all file changes and stage update.

**Per pending author:** silently skip.

**Console output:**
```
[import] 198 approved, 12 flagged, 21 pending
[import] OK (aktualisiert): maria-muster
[import] OK (unveraendert): peter-altmann
[import] FLAGGED (uebersprungen): hans-huber
[import] 198 reviewed, 12 flagged zum Nachbearbeiten
```

---

## State Machine

```
rendered → reviewed    (import: approved row, no errors)
rendered → rendered    (import: flagged row — stays, logged for follow-up)
rendered → failed      (import: exception during file write or render)
```

`update_stage` from `scraper/state.py` handles all transitions — no changes to state.py needed.

---

## New Files

| File | Purpose |
|---|---|
| `review/export.py` | Export rendered authors to CSV |
| `review/import.py` | Import reviewed CSV, update JSON + richsnippets |
| `review/__init__.py` | Empty — makes review/ a package for imports |
| `tests/test_review_export.py` | Unit tests for export logic |
| `tests/test_review_import.py` | Unit tests for import logic |

## Modified Files

| File | Change |
|---|---|
| `.gitignore` | Add `review/author_review.csv` |

## Unchanged Files

- `scraper/state.py` — `update_stage` and `get_authors_by_stage` already generic
- `scraper/render.py` — `render_jsonld` called directly, no changes needed
- `pipeline.py` — review is standalone, not a pipeline stage

---

## Testing

**`tests/test_review_export.py`:**
- Exports correct columns and headers
- All `rendered` authors appear in CSV with `status = pending`
- Beats spread across `beat_1`…`beat_5` correctly
- Authors with fewer than 5 beats have empty cells in remaining columns
- Non-`rendered` authors (generated, inactive) are excluded

**`tests/test_review_import.py`:**
- Approved row with changed bio updates `data/authors/{slug}.json`
- Approved row with changed bio triggers richsnippet re-render
- Approved row with no changes does not touch files but still calls `update_stage("reviewed")`
- Flagged row: no file changes, no `update_stage` call, logged
- Pending row: silently skipped
- Empty `beat_*` cells are ignored (not written as empty strings to beats array)
- Import is idempotent — running twice on the same CSV produces the same result