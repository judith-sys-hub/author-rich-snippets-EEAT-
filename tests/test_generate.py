import pytest
from unittest.mock import MagicMock
from scraper.generate import build_prompt, generate_bio, SYSTEM_PROMPT


@pytest.fixture
def full_author():
    return {
        "profile": {
            "name": "Anna-Maria Aichholzer",
            "title": "Redakteurin News & Social Media",
            "bio_existing": "Gebürtige Salzburgerin und seit 2016 im Journalismus.",
            "bio_generated": None,
        },
        "expertise": {"beats": [], "derived_from_articles": False},
        "articles": [
            {"title": f"Artikel {i}", "section": "Graz", "published_at": f"2025-0{(i % 9) + 1}-01"}
            for i in range(12)
        ],
        "enrichment": {
            "awards": [{"title": "KLZ Award 2024", "source_url": "https://horizont.at/x", "verified": False}],
        },
    }


@pytest.fixture
def minimal_author():
    return {
        "profile": {"name": "Max Muster", "title": None, "bio_existing": None},
        "expertise": {"beats": [], "derived_from_articles": False},
        "articles": [],
        "enrichment": {"awards": []},
    }


def test_build_prompt_includes_name(full_author):
    assert "Anna-Maria Aichholzer" in build_prompt(full_author)


def test_build_prompt_includes_title(full_author):
    assert "Redakteurin News & Social Media" in build_prompt(full_author)


def test_build_prompt_includes_existing_bio(full_author):
    assert "Gebürtige Salzburgerin" in build_prompt(full_author)


def test_build_prompt_omits_bio_section_when_null(minimal_author):
    assert "Bestehende Biografie" not in build_prompt(minimal_author)


def test_build_prompt_includes_articles(full_author):
    prompt = build_prompt(full_author)
    assert "Artikel 0" in prompt
    assert "Artikel 1" in prompt


def test_build_prompt_caps_at_10_articles(full_author):
    prompt = build_prompt(full_author)
    assert "Artikel 9" in prompt
    assert "Artikel 10" not in prompt


def test_build_prompt_includes_award(full_author):
    assert "KLZ Award 2024" in build_prompt(full_author)


def test_build_prompt_works_with_minimal_author(minimal_author):
    assert "Max Muster" in build_prompt(minimal_author)
