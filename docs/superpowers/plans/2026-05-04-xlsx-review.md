# Styled Excel Review File Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the plain CSV review file with a formatted `.xlsx` that editors can open in Google Sheets — with readable bios, color-coded status, beats in a single column, and a live progress summary row.

**Architecture:** `review/export.py` gains `write_xlsx()` (all openpyxl logic) and `build_row()` switches from `beat_1…beat_5` to a single `themen` key. `review/importer.py` gains `read_xlsx()` and `parse_beats_from_themen()`, replacing the old CSV and beat-column logic. Both tests are fully rewritten for xlsx fixtures.

**Tech Stack:** Python 3.14, openpyxl>=3.1, pytest, unittest.mock. No other new dependencies.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `review/__init__.py` | MODIFY | Clear constants (becomes empty) |
| `review/export.py` | MODIFY | `build_row()` → `themen`; add `write_xlsx()`; `export_authors()` → xlsx |
| `review/importer.py` | MODIFY | Add `parse_beats_from_themen()`, `read_xlsx()`; update `import_authors()` |
| `requirements.txt` | MODIFY | Add `openpyxl>=3.1` |
| `.gitignore` | MODIFY | `review/author_review.csv` → `review/author_review.xlsx` |
| `tests/test_review_export.py` | MODIFY | Rewrite for xlsx; add formatting/validation tests |
| `tests/test_review_import.py` | MODIFY | Rewrite for xlsx; replace `parse_beats` tests with `parse_beats_from_themen` |

---

### Task 1: `review/export.py` + `review/__init__.py` + `tests/test_review_export.py`

**Files:**
- Modify: `review/__init__.py`
- Modify: `review/export.py`
- Modify: `requirements.txt`
- Modify: `tests/test_review_export.py`

- [ ] **Step 1: Install openpyxl**

```
pip install openpyxl>=3.1
```

Then add to `requirements.txt` (after the existing entries):

```
openpyxl>=3.1
```

- [ ] **Step 2: Write failing tests**

Replace the entire contents of `tests/test_review_export.py` with:

```python
import json
from pathlib import Path
from unittest.mock import patch

import openpyxl
import pytest

from review.export import build_row, export_authors, write_xlsx


def _make_author(slug="test-autor", beats=None, bio="Ein Redakteur."):
    if beats is None:
        beats = ["Sport", "Fussball"]
    return {
        "meta": {"slug": slug},
        "profile": {"name": "Test Autor", "bio_generated": bio},
        "expertise": {"beats": beats, "derived_from_articles": True},
        "articles": [],
        "enrichment": {"awards": [], "social_links": {}, "wikipedia_url": None},
    }


def _read_data_rows(xlsx_path: Path) -> list[dict]:
    """Read data rows (row 3+) as list of dicts, skipping summary and header."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = []
    for row_vals in ws.iter_rows(min_row=3, values_only=True):
        padded = list(row_vals) + [None] * 5
        slug, name, status, bio, themen = padded[:5]
        if slug:
            rows.append({"slug": slug, "name": name, "status": status, "bio": bio, "themen": themen})
    return rows


# --- build_row unit tests ---

def test_build_row_slug():
    assert build_row(_make_author(slug="maria-muster"))["slug"] == "maria-muster"


def test_build_row_name():
    assert build_row(_make_author())["name"] == "Test Autor"


def test_build_row_status_is_pending():
    assert build_row(_make_author())["status"] == "pending"


def test_build_row_bio():
    assert build_row(_make_author(bio="Eine Journalistin."))["bio"] == "Eine Journalistin."


def test_build_row_themen_semicolon_joined():
    assert build_row(_make_author(beats=["Sport", "Fussball", "Tennis"]))["themen"] == "Sport; Fussball; Tennis"


def test_build_row_no_beats_empty_themen():
    assert build_row(_make_author(beats=[]))["themen"] == ""


def test_build_row_missing_expertise():
    author = _make_author()
    del author["expertise"]
    assert build_row(author)["themen"] == ""


def test_build_row_null_beats():
    author = _make_author()
    author["expertise"]["beats"] = None
    assert build_row(author)["themen"] == ""


def test_build_row_null_bio():
    author = _make_author()
    author["profile"]["bio_generated"] = None
    assert build_row(author)["bio"] == ""


# --- write_xlsx unit tests ---

def test_write_xlsx_creates_file(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    write_xlsx([{"slug": "a", "name": "A", "status": "pending", "bio": "Bio.", "themen": "Sport"}], xlsx_path)
    assert xlsx_path.exists()


def test_write_xlsx_header_row(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    write_xlsx([], xlsx_path)
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    assert ws.cell(row=2, column=1).value == "slug"
    assert ws.cell(row=2, column=3).value == "status"
    assert ws.cell(row=2, column=5).value == "themen"


def test_write_xlsx_summary_row_has_countif_formula(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    write_xlsx([{"slug": "a", "name": "A", "status": "pending", "bio": "Bio.", "themen": "Sport"}], xlsx_path)
    wb = openpyxl.load_workbook(xlsx_path)  # no data_only — need formula text
    ws = wb.active
    assert str(ws["C1"].value).startswith("=COUNTIF")


def test_write_xlsx_data_row_values(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    rows = [{"slug": "maria-muster", "name": "Maria Muster", "status": "pending", "bio": "Eine Bio.", "themen": "Sport; Fussball"}]
    write_xlsx(rows, xlsx_path)
    data = _read_data_rows(xlsx_path)
    assert data[0]["slug"] == "maria-muster"
    assert data[0]["status"] == "pending"
    assert data[0]["bio"] == "Eine Bio."
    assert data[0]["themen"] == "Sport; Fussball"


def test_write_xlsx_conditional_formatting_present(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    write_xlsx([{"slug": "a", "name": "A", "status": "pending", "bio": "Bio.", "themen": ""}], xlsx_path)
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    assert len(list(ws.conditional_formatting)) > 0


def test_write_xlsx_data_validation_present(tmp_path):
    xlsx_path = tmp_path / "test.xlsx"
    write_xlsx([{"slug": "a", "name": "A", "status": "pending", "bio": "Bio.", "themen": ""}], xlsx_path)
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    assert len(ws.data_validations.dataValidation) > 0


# --- export_authors integration tests ---

def test_export_returns_count(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        count = export_authors(data_dir=data_dir, xlsx_path=xlsx_path)
    assert count == 1


def test_export_writes_xlsx_file(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, xlsx_path=xlsx_path)
    assert xlsx_path.exists()


def test_export_row_values(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author(slug="test-autor", beats=["Sport", "Fussball"], bio="Ein Sportredakteur.")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, xlsx_path=xlsx_path)
    rows = _read_data_rows(xlsx_path)
    assert rows[0]["slug"] == "test-autor"
    assert rows[0]["status"] == "pending"
    assert rows[0]["bio"] == "Ein Sportredakteur."
    assert rows[0]["themen"] == "Sport; Fussball"


def test_export_overwrites_existing_file(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    xlsx_path.write_bytes(b"stale")
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, xlsx_path=xlsx_path)
    wb = openpyxl.load_workbook(xlsx_path)
    assert wb.active.cell(row=2, column=1).value == "slug"


def test_export_skips_missing_json_file(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "ghost-autor"}]):
        count = export_authors(data_dir=data_dir, xlsx_path=xlsx_path)
    assert count == 0
```

- [ ] **Step 3: Run tests — verify they fail**

```
pytest tests/test_review_export.py -v
```

Expected: failures on `write_xlsx` (not defined), `build_row` (no `themen` key), and xlsx-related assertions.

- [ ] **Step 4: Clear `review/__init__.py`**

Replace the entire contents of `review/__init__.py` with an empty file:

```python
```

(The file must remain so `review` stays a valid Python package.)

- [ ] **Step 5: Rewrite `review/export.py`**

Replace the entire contents of `review/export.py` with:

```python
import json
from pathlib import Path

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.worksheet.datavalidation import DataValidation

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
XLSX_PATH = Path(__file__).parent / "author_review.xlsx"


def build_row(author_data: dict) -> dict:
    profile = author_data["profile"]
    beats = (author_data.get("expertise") or {}).get("beats") or []
    return {
        "slug": author_data["meta"]["slug"],
        "name": profile.get("name", ""),
        "status": "pending",
        "bio": profile.get("bio_generated") or "",
        "themen": "; ".join(beats),
    }


def write_xlsx(rows: list[dict], xlsx_path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Autorenreview"

    last_row = len(rows) + 2  # row 1 summary + row 2 header + data rows

    # Row 1: summary with live COUNTIF formulas
    summary_fill = PatternFill("solid", fgColor="E3F2FD")
    summary_font = Font(bold=True)
    ws["A1"] = "Fortschritt"
    ws["B1"] = f"=COUNTA(A3:A{last_row})"
    ws["C1"] = f'=COUNTIF(C3:C{last_row},"approved")'
    ws["D1"] = f'=COUNTIF(C3:C{last_row},"pending")'
    ws["E1"] = f'=COUNTIF(C3:C{last_row},"flagged")'
    for col in "ABCDE":
        ws[f"{col}1"].fill = summary_fill
        ws[f"{col}1"].font = summary_font

    # Row 2: headers (frozen)
    header_fill = PatternFill("solid", fgColor="E8EAF6")
    header_font = Font(bold=True)
    for i, col_name in enumerate(["slug", "name", "status", "bio", "themen"], start=1):
        cell = ws.cell(row=2, column=i, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
    ws.freeze_panes = "A3"

    # Data rows
    grey_font = Font(color="BBBBBB")
    wrap_align = Alignment(wrap_text=True, vertical="top")
    for r_idx, row in enumerate(rows, start=3):
        ws.cell(row=r_idx, column=1, value=row["slug"]).font = grey_font
        ws.cell(row=r_idx, column=2, value=row["name"])
        ws.cell(row=r_idx, column=3, value=row["status"])
        bio_cell = ws.cell(row=r_idx, column=4, value=row["bio"])
        bio_cell.alignment = wrap_align
        ws.cell(row=r_idx, column=5, value=row["themen"])
        ws.row_dimensions[r_idx].height = 60

    # Column widths
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 60
    ws.column_dimensions["E"].width = 35

    # Conditional formatting on column C
    cf_range = f"C3:C{last_row}"
    ws.conditional_formatting.add(
        cf_range,
        CellIsRule(operator="equal", formula=['"approved"'], fill=PatternFill("solid", fgColor="C8E6C9")),
    )
    ws.conditional_formatting.add(
        cf_range,
        CellIsRule(operator="equal", formula=['"flagged"'], fill=PatternFill("solid", fgColor="FFCDD2")),
    )
    ws.conditional_formatting.add(
        cf_range,
        CellIsRule(operator="equal", formula=['"pending"'], fill=PatternFill("solid", fgColor="FFF9C4")),
    )

    # Data validation dropdown on column C
    dv = DataValidation(type="list", formula1='"pending,approved,flagged"', allow_blank=False)
    dv.sqref = f"C3:C{last_row}"
    ws.add_data_validation(dv)

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(xlsx_path)


def export_authors(data_dir: Path = DATA_DIR, xlsx_path: Path = XLSX_PATH) -> int:
    from scraper.state import get_authors_by_stage

    candidates = list(get_authors_by_stage("rendered"))
    rows = []
    for candidate in candidates:
        slug = candidate["slug"]
        json_path = data_dir / f"{slug}.json"
        if not json_path.exists():
            print(f"[export] WARNUNG: {json_path.name} nicht gefunden – uebersprungen")
            continue
        author_data = json.loads(json_path.read_text(encoding="utf-8"))
        try:
            rows.append(build_row(author_data))
        except Exception as exc:
            raise RuntimeError(f"Fehler bei {slug}: {exc}") from exc

    write_xlsx(rows, xlsx_path)
    return len(rows)


if __name__ == "__main__":
    count = export_authors()
    print(f"[export] {count} Autoren exportiert -> {XLSX_PATH}")
```

- [ ] **Step 6: Run tests — verify they pass**

```
pytest tests/test_review_export.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```
git add review/__init__.py review/export.py requirements.txt tests/test_review_export.py
git commit -m "feat: export styled xlsx instead of csv (Sub-project 5, task 1)"
```

---

### Task 2: `review/importer.py` + `tests/test_review_import.py` + `.gitignore` + smoke test

**Files:**
- Modify: `review/importer.py`
- Modify: `tests/test_review_import.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing tests**

Replace the entire contents of `tests/test_review_import.py` with:

```python
import json
from pathlib import Path
from unittest.mock import patch

import openpyxl
import pytest

from review.importer import parse_beats_from_themen, import_authors


def _write_xlsx(xlsx_path: Path, rows: list[dict]) -> None:
    """Write minimal xlsx fixture: summary row + header row + data rows."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Fortschritt", "Gesamt", "approved", "pending", "flagged"])  # row 1 summary
    ws.append(["slug", "name", "status", "bio", "themen"])                  # row 2 headers
    for row in rows:
        ws.append([row["slug"], row["name"], row["status"], row["bio"], row.get("themen", "")])
    wb.save(xlsx_path)


def _make_author_json(slug="test-autor", bio="Ein Redakteur.", beats=None):
    if beats is None:
        beats = ["Sport"]
    return {
        "meta": {"slug": slug},
        "profile": {
            "name": "Test Autor",
            "title": "Redakteur",
            "bio_generated": bio,
            "profile_url": f"https://www.kleinezeitung.at/autor/1/{slug}",
            "photo_url": None,
        },
        "expertise": {"beats": beats, "derived_from_articles": True},
        "articles": [],
        "enrichment": {
            "awards": [],
            "social_links": {"linkedin": None, "instagram": None},
            "wikipedia_url": None,
        },
    }


def _make_row(slug="test-autor", status="approved", bio="Ein Redakteur.", themen="Sport"):
    return {"slug": slug, "name": "Test Autor", "status": status, "bio": bio, "themen": themen}


# --- parse_beats_from_themen unit tests ---

def test_parse_beats_from_themen_basic():
    assert parse_beats_from_themen("Sport; Fussball; Tennis") == ["Sport", "Fussball", "Tennis"]


def test_parse_beats_from_themen_empty_string():
    assert parse_beats_from_themen("") == []


def test_parse_beats_from_themen_strips_whitespace():
    assert parse_beats_from_themen("  Sport ;  Fussball  ") == ["Sport", "Fussball"]


def test_parse_beats_from_themen_single_beat():
    assert parse_beats_from_themen("Sport") == ["Sport"]


# --- import_authors integration tests ---

def test_import_approved_changed_bio_updates_json(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Alter Text.")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(bio="Neuer Text.", themen="Sport")])
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    updated = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert updated["profile"]["bio_generated"] == "Neuer Text."


def test_import_approved_changed_themen_updates_beats(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Bio.", beats=["Sport"])
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(bio="Bio.", themen="Kultur; Politik")])
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    updated = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert updated["expertise"]["beats"] == ["Kultur", "Politik"]


def test_import_approved_changed_bio_rerenders_richsnippet(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Alter Text.")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(bio="Neuer Text.", themen="Sport")])
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    out = richsnippet_dir / "test-autor.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["@context"] == "https://schema.org"


def test_import_approved_unchanged_does_not_write_files(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Ein Redakteur.", beats=["Sport"])
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    mtime_before = (data_dir / "test-autor.json").stat().st_mtime
    _write_xlsx(xlsx_path, [_make_row(bio="Ein Redakteur.", themen="Sport")])
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    assert (data_dir / "test-autor.json").stat().st_mtime == mtime_before
    assert not (richsnippet_dir / "test-autor.json").exists()


def test_import_approved_calls_update_stage_reviewed(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Ein Redakteur.", beats=["Sport"])
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(bio="Ein Redakteur.", themen="Sport")])
    with patch("scraper.state.update_stage") as mock_update:
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    mock_update.assert_called_once_with("test-autor", "reviewed")


def test_import_flagged_skips_file_changes(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Original.")
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(status="flagged", bio="Edited.", themen="Sport")])
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    unchanged = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert unchanged["profile"]["bio_generated"] == "Original."


def test_import_flagged_no_update_stage(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json()
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(status="flagged")])
    with patch("scraper.state.update_stage") as mock_update:
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    mock_update.assert_not_called()


def test_import_pending_silently_skipped(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json()
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(status="pending")])
    with patch("scraper.state.update_stage") as mock_update:
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    mock_update.assert_not_called()


def test_import_returns_counts(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    for slug in ["a", "b", "c"]:
        author = _make_author_json(slug=slug)
        (data_dir / f"{slug}.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    rows = [
        _make_row(slug="a", status="approved", bio="Ein Redakteur.", themen="Sport"),
        _make_row(slug="b", status="flagged", themen="Sport"),
        _make_row(slug="c", status="pending", themen="Sport"),
    ]
    _write_xlsx(xlsx_path, rows)
    with patch("scraper.state.update_stage"):
        counts = import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    assert counts["approved"] == 1
    assert counts["flagged"] == 1
    assert counts["pending"] == 1


def test_import_idempotent(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Alter Text.", beats=["Kultur"])
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(bio="Neuer Text.", themen="Sport")])
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    mtime_after_first = (data_dir / "test-autor.json").stat().st_mtime
    with patch("scraper.state.update_stage"):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    assert (data_dir / "test-autor.json").stat().st_mtime == mtime_after_first


def test_import_approved_missing_expertise_does_not_crash(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    author = _make_author_json(bio="Alter Text.", beats=["Sport"])
    del author["expertise"]
    (data_dir / "test-autor.json").write_text(json.dumps(author, ensure_ascii=False), encoding="utf-8")
    _write_xlsx(xlsx_path, [_make_row(bio="Neuer Text.", themen="Kultur")])
    with patch("scraper.state.update_stage") as mock_update:
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    updated = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert updated["expertise"]["beats"] == ["Kultur"]
    mock_update.assert_called_once_with("test-autor", "reviewed")


def test_import_approved_missing_json_file_does_not_crash(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "author_review.xlsx"
    _write_xlsx(xlsx_path, [_make_row(slug="ghost-autor", bio="Bio.", themen="Sport")])
    with patch("scraper.state.update_stage") as mock_update:
        counts = import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
    mock_update.assert_not_called()
    assert counts["approved"] == 1


def test_import_missing_xlsx_file_raises_error(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    xlsx_path = tmp_path / "does_not_exist.xlsx"
    with pytest.raises(FileNotFoundError):
        import_authors(xlsx_path=xlsx_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_review_import.py -v
```

Expected: failures — `parse_beats_from_themen` not defined, `import_authors` still reads CSV.

- [ ] **Step 3: Rewrite `review/importer.py`**

Replace the entire contents of `review/importer.py` with:

```python
import json
from pathlib import Path

import openpyxl

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
RICHSNIPPET_DIR = Path(__file__).parent.parent / "richsnippet"
XLSX_PATH = Path(__file__).parent / "author_review.xlsx"


def parse_beats_from_themen(themen: str) -> list[str]:
    if not themen or not themen.strip():
        return []
    return [b.strip() for b in themen.split(";") if b.strip()]


def read_xlsx(xlsx_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = []
    for row_vals in ws.iter_rows(min_row=3, values_only=True):
        padded = list(row_vals) + [None] * 5
        slug, name, status, bio, themen = padded[:5]
        if not slug:
            continue
        rows.append({
            "slug": str(slug).strip(),
            "name": str(name or ""),
            "status": str(status or "").strip().lower(),
            "bio": str(bio or "").strip(),
            "themen": str(themen or "").strip(),
        })
    return rows


def import_authors(
    xlsx_path: Path = XLSX_PATH,
    data_dir: Path = DATA_DIR,
    richsnippet_dir: Path = RICHSNIPPET_DIR,
) -> dict:
    from scraper.render import render_jsonld
    from scraper.state import update_stage

    counts = {"approved": 0, "flagged": 0, "pending": 0}
    flagged = []

    rows = read_xlsx(xlsx_path)

    for row in rows:
        status = row["status"]
        slug = row["slug"]

        if status == "flagged":
            counts["flagged"] += 1
            flagged.append(slug)
            continue
        if status != "approved":
            counts["pending"] += 1
            continue

        counts["approved"] += 1
        json_path = data_dir / f"{slug}.json"
        if not json_path.exists():
            print(f"[import] FEHLER: {json_path.name} nicht gefunden – uebersprungen")
            continue
        author_data = json.loads(json_path.read_text(encoding="utf-8"))

        new_bio = row["bio"]
        new_beats = parse_beats_from_themen(row["themen"])
        current_bio = author_data["profile"].get("bio_generated") or ""
        current_beats = (author_data.get("expertise") or {}).get("beats") or []

        try:
            if new_bio != current_bio or new_beats != current_beats:
                author_data["profile"]["bio_generated"] = new_bio
                if author_data.get("expertise") is None:
                    author_data["expertise"] = {"beats": [], "derived_from_articles": False}
                author_data["expertise"]["beats"] = new_beats
                json_path.write_text(
                    json.dumps(author_data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                jsonld = render_jsonld(author_data)
                (richsnippet_dir / f"{slug}.json").write_text(
                    json.dumps(jsonld, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"[import] OK (aktualisiert): {slug}")
            else:
                print(f"[import] OK (unveraendert): {slug}")
            update_stage(slug, "reviewed")
        except Exception as exc:
            print(f"[import] FEHLER: {slug} – {exc}")

    for slug in flagged:
        print(f"[import] FLAGGED (uebersprungen): {slug}")

    print(
        f"[import] {counts['approved']} reviewed, "
        f"{counts['flagged']} flagged zum Nachbearbeiten"
    )
    return counts


if __name__ == "__main__":
    import_authors()
```

- [ ] **Step 4: Run import tests — verify they pass**

```
pytest tests/test_review_import.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Update `.gitignore`**

In `.gitignore`, replace:

```
review/author_review.csv
```

with:

```
review/author_review.xlsx
```

- [ ] **Step 6: Run full test suite**

```
pytest tests/ -v
```

Expected: export and import tests all pass. Pre-existing failures in `test_articles.py` and `test_discover.py` (11 failures from scraper CSS changes) are unrelated — ignore them. All other tests should pass.

- [ ] **Step 7: Smoke test — export real data**

```
python -m review.export
```

Expected output:
```
[export] 231 Autoren exportiert -> C:\Users\denkmaju\GeminiWorkspace\author-profiles\review\author_review.xlsx
```

Open `review/author_review.xlsx` in Google Sheets and verify:
- Row 1 shows summary labels and formula cells
- Row 2 has headers: slug / name / status / bio / themen
- Data rows start at row 3
- Bio column has wrapped text
- Status column offers a dropdown when clicking a cell

- [ ] **Step 8: Commit**

```
git add review/importer.py tests/test_review_import.py .gitignore
git commit -m "feat: importer reads xlsx, beats via themen column (Sub-project 5, task 2)"
```
