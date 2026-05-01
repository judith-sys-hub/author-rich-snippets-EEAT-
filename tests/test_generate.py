import pytest
from unittest.mock import MagicMock
from scraper.generate import build_prompt, generate_bio, SYSTEM_PROMPT


@pytest.fixture
def full_author():
    return {
        "profile": {
            "name": "Anna-Maria Aichholzer",
            "title": "Redakteurin News & Social Media",
            "bio_existing": "GebÃ¼rtige Salzburgerin und seit 2016 im Journalismus.",
            "bio_generated": None,
        },
        "expertise": {"beats": [], "derived_from_articles": False},
        "articles": [
            {"title": f"Artikel {i}", "section": "Graz", "published_at": f"2025-{i + 1:02d}-01"}
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
    assert "GebÃ¼rtige Salzburgerin" in build_prompt(full_author)


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


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def test_generate_bio_sets_bio_generated(full_author):
    client = _mock_client('{"bio": "Eine erfahrene Journalistin.", "beats": ["Social Media"]}')
    result = generate_bio(full_author, client, SYSTEM_PROMPT)
    assert result["profile"]["bio_generated"] == "Eine erfahrene Journalistin."


def test_generate_bio_sets_beats(full_author):
    client = _mock_client('{"bio": "Eine erfahrene Journalistin.", "beats": ["Social Media", "Graz"]}')
    result = generate_bio(full_author, client, SYSTEM_PROMPT)
    assert result["expertise"]["beats"] == ["Social Media", "Graz"]


def test_generate_bio_sets_derived_from_articles(full_author):
    client = _mock_client('{"bio": "Journalistin.", "beats": ["Graz"]}')
    result = generate_bio(full_author, client, SYSTEM_PROMPT)
    assert result["expertise"]["derived_from_articles"] is True


def test_generate_bio_raises_on_unparseable_response(full_author):
    client = _mock_client("Das ist kein gültiges JSON und enthält keine geschweifte Klammer")
    with pytest.raises(ValueError, match="Could not parse JSON"):
        generate_bio(full_author, client, SYSTEM_PROMPT)


def test_generate_bio_recovers_json_embedded_in_text(full_author):
    client = _mock_client('Hier ist die Antwort: {"bio": "Journalistin.", "beats": ["Graz"]} Ende.')
    result = generate_bio(full_author, client, SYSTEM_PROMPT)
    assert result["profile"]["bio_generated"] == "Journalistin."


def test_generate_bio_uses_cache_control(full_author):
    client = _mock_client('{"bio": "Journalistin.", "beats": ["Graz"]}')
    generate_bio(full_author, client, SYSTEM_PROMPT)
    call_kwargs = client.messages.create.call_args.kwargs
    system_blocks = call_kwargs["system"]
    assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
