# Author Review Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-script spreadsheet workflow — `review/export.py` and `review/importer.py` — that lets editors approve/edit generated author bios and beats in a CSV, then imports changes back into the JSON + richsnippet files.

**Architecture:** `export.py` reads all `rendered` authors from the DB, writes `review/author_review.csv` with one row per author (slug, name, status, bio, beat_1…beat_5). Editors edit in Excel/Sheets, change `status` to `approved` or `flagged`. `importer.py` reads the CSV, updates changed JSON files, re-renders affected richsnippets by calling `render_jsonld()` directly, and marks authors as `reviewed` in the DB.

**Tech Stack:** Python 3.14, pytest, stdlib only (`csv`, `json`, `pathlib`). Reuses `scraper/state.py` and `scraper/render.py` — no changes to either.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `review/__init__.py` | CREATE | Shared constants: `BEAT_COLS`, `FIELDNAMES` |
| `review/export.py` | CREATE | `build_row()` + `export_authors()` — DB → CSV |
| `review/importer.py` | CREATE | `parse_beats()` + `import_authors()` — CSV → JSON + richsnippets |
| `tests/test_review_export.py` | CREATE | Unit tests for build_row + export_authors |
| `tests/test_review_import.py` | CREATE | Unit tests for parse_beats + import_authors |
| `.gitignore` | MODIFY | Add `review/author_review.csv` |

> **Note:** The spec named the import script `import.py` — that name conflicts with Python's `import` keyword and cannot be used in test imports. `importer.py` is used instead. CLI usage: `python review/importer.py`.

---

### Task 1: `review/__init__.py` + `review/export.py`

**Files:**
- Create: `review/__init__.py`
- Create: `review/export.py`
- Create: `tests/test_review_export.py`

- [ ] **Step 1: Create `review/__init__.py`**

```python
BEAT_COLS = ["beat_1", "beat_2", "beat_3", "beat_4", "beat_5"]
FIELDNAMES = ["slug", "name", "status", "bio"] + BEAT_COLS
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_review_export.py`:

```python
import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from review.export import build_row, export_authors
from review import FIELDNAMES


def _make_author(slug="test-autor", beats=None, bio="Ein Redakteur."):
    if beats is None:
        beats = ["Sport", "Fussball"]
    return {
        "meta": {"slug": slug},
        "profile": {
            "name": "Test Autor",
            "bio_generated": bio,
        },
        "expertise": {"beats": beats, "derived_from_articles": True},
        "articles": [],
        "enrichment": {"awards": [], "social_links": {}, "wikipedia_url": None},
    }


# --- build_row unit tests ---

def test_build_row_slug():
    row = build_row(_make_author(slug="maria-muster"))
    assert row["slug"] == "maria-muster"


def test_build_row_name():
    row = build_row(_make_author())
    assert row["name"] == "Test Autor"


def test_build_row_status_is_pending():
    row = build_row(_make_author())
    assert row["status"] == "pending"


def test_build_row_bio():
    row = build_row(_make_author(bio="Eine Journalistin."))
    assert row["bio"] == "Eine Journalistin."


def test_build_row_beats_spread_across_columns():
    row = build_row(_make_author(beats=["Sport", "Fussball", "Tennis"]))
    assert row["beat_1"] == "Sport"
    assert row["beat_2"] == "Fussball"
    assert row["beat_3"] == "Tennis"


def test_build_row_empty_beat_columns_when_fewer_than_5():
    row = build_row(_make_author(beats=["Sport"]))
    assert row["beat_2"] == ""
    assert row["beat_3"] == ""
    assert row["beat_4"] == ""
    assert row["beat_5"] == ""


def test_build_row_5_beats():
    row = build_row(_make_author(beats=["a", "b", "c", "d", "e"]))
    assert row["beat_5"] == "e"


# --- export_authors integration tests ---

def test_export_returns_count(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        count = export_authors(data_dir=data_dir, csv_path=csv_path)
    assert count == 1


def test_export_writes_csv_file(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, csv_path=csv_path)
    assert csv_path.exists()


def test_export_csv_has_correct_headers(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, csv_path=csv_path)
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDNAMES


def test_export_csv_row_values(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"
    author = _make_author(slug="test-autor", beats=["Sport", "Fussball"], bio="Ein Sportredakteur.")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, csv_path=csv_path)
    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["slug"] == "test-autor"
    assert rows[0]["status"] == "pending"
    assert rows[0]["bio"] == "Ein Sportredakteur."
    assert rows[0]["beat_1"] == "Sport"
    assert rows[0]["beat_2"] == "Fussball"
    assert rows[0]["beat_3"] == ""


def test_export_overwrites_existing_file(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"
    csv_path.write_text("stale content", encoding="utf-8")
    author = _make_author(slug="test-autor")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        export_authors(data_dir=data_dir, csv_path=csv_path)
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDNAMES
```

- [ ] **Step 3: Run tests — verify they fail**

```
pytest tests/test_review_export.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError: No module named 'review.export'`

- [ ] **Step 4: Create `review/export.py`**

```python
import csv
import json
from pathlib import Path

from review import BEAT_COLS, FIELDNAMES

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
CSV_PATH = Path(__file__).parent / "author_review.csv"


def build_row(author_data: dict) -> dict:
    profile = author_data["profile"]
    beats = (author_data.get("expertise") or {}).get("beats") or []
    row = {
        "slug": author_data["meta"]["slug"],
        "name": profile.get("name", ""),
        "status": "pending",
        "bio": profile.get("bio_generated") or "",
    }
    for i, col in enumerate(BEAT_COLS):
        row[col] = beats[i] if i < len(beats) else ""
    return row


def export_authors(data_dir: Path = DATA_DIR, csv_path: Path = CSV_PATH) -> int:
    from scraper.state import get_authors_by_stage

    candidates = list(get_authors_by_stage("rendered"))
    rows = []
    for row in candidates:
        slug = row["slug"]
        author_data = json.loads(
            (data_dir / f"{slug}.json").read_text(encoding="utf-8")
        )
        rows.append(build_row(author_data))

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


if __name__ == "__main__":
    count = export_authors()
    print(f"[export] {count} Autoren exportiert → {CSV_PATH}")
```

- [ ] **Step 5: Run tests — verify they pass**

```
pytest tests/test_review_export.py -v
```

Expected: all 12 tests PASS

---

### Task 2: `review/importer.py` + `.gitignore` + smoke test

**Files:**
- Create: `review/importer.py`
- Create: `tests/test_review_import.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing tests**

Create `tests/test_review_import.py`:

```python
import csv
import json
from pathlib import Path
from unittest.mock import patch, call

import pytest

from review.importer import parse_beats, import_authors
from review import FIELDNAMES


def _write_csv(csv_path: Path, rows: list[dict]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


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


def _make_row(slug="test-autor", status="approved", bio="Ein Redakteur.", beat_1="Sport", beat_2="", beat_3="", beat_4="", beat_5=""):
    return {
        "slug": slug, "name": "Test Autor", "status": status,
        "bio": bio, "beat_1": beat_1, "beat_2": beat_2,
        "beat_3": beat_3, "beat_4": beat_4, "beat_5": beat_5,
    }


# --- parse_beats unit tests ---

def test_parse_beats_returns_non_empty():
    row = _make_row(beat_1="Sport", beat_2="Fussball", beat_3="")
    assert parse_beats(row) == ["Sport", "Fussball"]


def test_parse_beats_filters_empty_strings():
    row = _make_row(beat_1="Sport", beat_2="", beat_3="", beat_4="", beat_5="")
    assert parse_beats(row) == ["Sport"]


def test_parse_beats_strips_whitespace():
    row = _make_row(beat_1="  Sport  ", beat_2="  ", beat_3="")
    assert parse_beats(row) == ["Sport"]


def test_parse_beats_all_empty():
    row = _make_row(beat_1="", beat_2="", beat_3="", beat_4="", beat_5="")
    assert parse_beats(row) == []


# --- import_authors integration tests ---

def test_import_approved_changed_bio_updates_json(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Alter Text.")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(bio="Neuer Text.", beat_1="Sport")])

    with patch("scraper.state.update_stage"):
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    updated = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert updated["profile"]["bio_generated"] == "Neuer Text."


def test_import_approved_changed_bio_rerenders_richsnippet(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Alter Text.")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(bio="Neuer Text.", beat_1="Sport")])

    with patch("scraper.state.update_stage"):
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    out = richsnippet_dir / "test-autor.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["@context"] == "https://schema.org"


def test_import_approved_unchanged_does_not_write_files(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Ein Redakteur.", beats=["Sport"])
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    mtime_before = (data_dir / "test-autor.json").stat().st_mtime
    _write_csv(csv_path, [_make_row(bio="Ein Redakteur.", beat_1="Sport")])

    with patch("scraper.state.update_stage"):
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    assert (data_dir / "test-autor.json").stat().st_mtime == mtime_before
    assert not (richsnippet_dir / "test-autor.json").exists()


def test_import_approved_calls_update_stage_reviewed(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Ein Redakteur.", beats=["Sport"])
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(bio="Ein Redakteur.", beat_1="Sport")])

    with patch("scraper.state.update_stage") as mock_update:
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    mock_update.assert_called_once_with("test-autor", "reviewed")


def test_import_flagged_skips_file_changes(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Original.")
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(status="flagged", bio="Edited.")])

    with patch("scraper.state.update_stage"):
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    unchanged = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert unchanged["profile"]["bio_generated"] == "Original."


def test_import_flagged_no_update_stage(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json()
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(status="flagged")])

    with patch("scraper.state.update_stage") as mock_update:
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    mock_update.assert_not_called()


def test_import_pending_silently_skipped(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json()
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(status="pending")])

    with patch("scraper.state.update_stage") as mock_update:
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    mock_update.assert_not_called()


def test_import_returns_counts(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    for slug, status in [("a", "approved"), ("b", "flagged"), ("c", "pending")]:
        author = _make_author_json(slug=slug)
        author["profile"]["profile_url"] = f"https://www.kleinezeitung.at/autor/1/{slug}"
        (data_dir / f"{slug}.json").write_text(
            json.dumps(author, ensure_ascii=False), encoding="utf-8"
        )

    rows = [
        _make_row(slug="a", status="approved", bio="Ein Redakteur.", beat_1="Sport"),
        {**_make_row(slug="b"), "status": "flagged"},
        {**_make_row(slug="c"), "status": "pending"},
    ]
    _write_csv(csv_path, rows)

    with patch("scraper.state.update_stage"):
        counts = import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    assert counts["approved"] == 1
    assert counts["flagged"] == 1
    assert counts["pending"] == 1


def test_import_idempotent(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Alter Text.", beats=["Kultur"])
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(bio="Neuer Text.", beat_1="Sport")])

    with patch("scraper.state.update_stage"):
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    mtime_after_first = (data_dir / "test-autor.json").stat().st_mtime

    with patch("scraper.state.update_stage"):
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    assert (data_dir / "test-autor.json").stat().st_mtime == mtime_after_first
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_review_import.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError: No module named 'review.importer'`

- [ ] **Step 3: Create `review/importer.py`**

```python
import csv
import json
from pathlib import Path

from review import BEAT_COLS, FIELDNAMES

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
RICHSNIPPET_DIR = Path(__file__).parent.parent / "richsnippet"
CSV_PATH = Path(__file__).parent / "author_review.csv"


def parse_beats(row: dict) -> list[str]:
    return [row[col].strip() for col in BEAT_COLS if row.get(col, "").strip()]


def import_authors(
    csv_path: Path = CSV_PATH,
    data_dir: Path = DATA_DIR,
    richsnippet_dir: Path = RICHSNIPPET_DIR,
) -> dict:
    from scraper.render import render_jsonld
    from scraper.state import update_stage

    counts = {"approved": 0, "flagged": 0, "pending": 0}
    flagged = []

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        status = row["status"].strip().lower()
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
        author_data = json.loads(json_path.read_text(encoding="utf-8"))

        new_bio = row["bio"].strip()
        new_beats = parse_beats(row)
        current_bio = author_data["profile"].get("bio_generated") or ""
        current_beats = (author_data.get("expertise") or {}).get("beats") or []

        if new_bio != current_bio or new_beats != current_beats:
            author_data["profile"]["bio_generated"] = new_bio
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

Expected: all 13 tests PASS

- [ ] **Step 5: Run full test suite — verify no regressions**

```
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 6: Add `review/author_review.csv` to `.gitignore`**

Append to `C:\Users\denkmaju\GeminiWorkspace\author-profiles\.gitignore`:

```
review/author_review.csv
```

- [ ] **Step 7: Smoke test — export real data**

```
python review/export.py
```

Expected output:
```
[export] 231 Autoren exportiert → review\author_review.csv
```

Verify the file has the right shape:

```
python -c "import csv; rows=list(csv.DictReader(open('review/author_review.csv',encoding='utf-8'))); print(len(rows), 'rows;', rows[0]['slug'], '|', rows[0]['status'], '|', rows[0]['beat_1'])"
```

Expected: `231 rows; <slug> | pending | <first beat>`