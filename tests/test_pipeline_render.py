import json
from unittest.mock import patch

import pytest


@pytest.fixture
def author_json(tmp_path):
    data_dir = tmp_path / "authors"
    data_dir.mkdir()
    author_data = {
        "meta": {"slug": "test-autor"},
        "profile": {
            "name": "Test Autor",
            "title": "Redakteur",
            "bio_generated": "Ein Redakteur.",
            "profile_url": "https://www.kleinezeitung.at/autor/1/test-autor",
            "photo_url": None,
        },
        "expertise": {"beats": ["Sport"], "derived_from_articles": True},
        "articles": [],
        "enrichment": {
            "awards": [],
            "social_links": {"linkedin": None, "instagram": None},
            "wikipedia_url": None,
        },
    }
    (data_dir / "test-autor.json").write_text(
        json.dumps(author_data, ensure_ascii=False), encoding="utf-8"
    )
    return tmp_path


def test_run_render_writes_valid_jsonld(author_json, monkeypatch):
    import pipeline

    richsnippet_dir = author_json / "richsnippet"
    richsnippet_dir.mkdir()

    monkeypatch.setattr(pipeline, "DATA_DIR", author_json / "authors")
    monkeypatch.setattr(pipeline, "RICHSNIPPET_DIR", richsnippet_dir)

    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        with patch("scraper.state.update_stage") as mock_update:
            pipeline.run_render(dry_run=False, limit=None)

    mock_update.assert_called_once_with("test-autor", "rendered")
    out = richsnippet_dir / "test-autor.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["@context"] == "https://schema.org"
    assert data["@graph"][0]["@type"] == "Person"
    assert data["@graph"][0]["name"] == "Test Autor"


def test_run_render_dry_run_writes_no_file(author_json, monkeypatch):
    import pipeline

    richsnippet_dir = author_json / "richsnippet"
    richsnippet_dir.mkdir()

    monkeypatch.setattr(pipeline, "DATA_DIR", author_json / "authors")
    monkeypatch.setattr(pipeline, "RICHSNIPPET_DIR", richsnippet_dir)

    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        with patch("scraper.state.update_stage"):
            pipeline.run_render(dry_run=True, limit=None)

    assert not (richsnippet_dir / "test-autor.json").exists()


def test_run_render_handles_exception(author_json, monkeypatch):
    import pipeline

    richsnippet_dir = author_json / "richsnippet"
    richsnippet_dir.mkdir()

    monkeypatch.setattr(pipeline, "DATA_DIR", author_json / "authors")
    monkeypatch.setattr(pipeline, "RICHSNIPPET_DIR", richsnippet_dir)

    with patch("scraper.state.get_authors_by_stage", return_value=[{"slug": "test-autor"}]):
        with patch("scraper.render.render_jsonld", side_effect=ValueError("boom")):
            with patch("scraper.state.update_stage") as mock_update:
                pipeline.run_render(dry_run=False, limit=None)

    mock_update.assert_called_once_with("test-autor", "failed", error="boom")
    assert not (richsnippet_dir / "test-autor.json").exists()