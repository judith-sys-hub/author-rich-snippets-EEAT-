import csv
import json
from pathlib import Path
from unittest.mock import patch

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

    for slug in ["a", "b", "c"]:
        author = _make_author_json(slug=slug)
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


def test_import_approved_missing_expertise_does_not_crash(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    author = _make_author_json(bio="Alter Text.", beats=["Sport"])
    del author["expertise"]
    (data_dir / "test-autor.json").write_text(
        json.dumps(author, ensure_ascii=False), encoding="utf-8"
    )
    _write_csv(csv_path, [_make_row(bio="Neuer Text.", beat_1="Kultur")])

    with patch("scraper.state.update_stage") as mock_update:
        import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    updated = json.loads((data_dir / "test-autor.json").read_text(encoding="utf-8"))
    assert updated["expertise"]["beats"] == ["Kultur"]
    mock_update.assert_called_once_with("test-autor", "reviewed")


def test_import_approved_missing_json_file_does_not_crash(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    richsnippet_dir = tmp_path / "richsnippet"
    richsnippet_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"

    # CSV has slug "ghost-autor" but no corresponding JSON file
    _write_csv(csv_path, [_make_row(slug="ghost-autor", bio="Bio.", beat_1="Sport")])

    with patch("scraper.state.update_stage") as mock_update:
        counts = import_authors(csv_path=csv_path, data_dir=data_dir, richsnippet_dir=richsnippet_dir)

    mock_update.assert_not_called()
    assert counts["approved"] == 1  # counted as attempted