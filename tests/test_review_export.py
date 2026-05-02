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


def test_build_row_missing_expertise():
    author = _make_author()
    del author["expertise"]
    row = build_row(author)
    assert all(row[col] == "" for col in ["beat_1", "beat_2", "beat_3", "beat_4", "beat_5"])


def test_build_row_null_beats():
    author = _make_author()
    author["expertise"]["beats"] = None
    row = build_row(author)
    assert all(row[col] == "" for col in ["beat_1", "beat_2", "beat_3", "beat_4", "beat_5"])


def test_build_row_null_bio():
    author = _make_author()
    author["profile"]["bio_generated"] = None
    row = build_row(author)
    assert row["bio"] == ""


def test_export_skips_missing_json_file(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    csv_path = tmp_path / "author_review.csv"
    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "ghost-autor"}]):
        count = export_authors(data_dir=data_dir, csv_path=csv_path)
    assert count == 0
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert rows == []