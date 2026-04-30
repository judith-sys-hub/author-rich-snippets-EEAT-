import pytest


def test_empty_author_has_required_structure():
    from scraper.schema import empty_author
    a = empty_author("maria-muster", "Maria Muster",
                     "https://www.kleinezeitung.at/autor/maria-muster")
    assert a["meta"]["slug"] == "maria-muster"
    assert a["profile"]["name"] == "Maria Muster"
    assert a["expertise"]["beats"] == []
    assert a["expertise"]["derived_from_articles"] is False
    assert a["articles"] == []
    assert a["enrichment"]["awards"] == []
    assert a["enrichment"]["social_links"]["linkedin"] is None


def test_validate_author_passes_on_valid():
    from scraper.schema import empty_author, validate_author
    validate_author(empty_author("slug", "Name",
                                 "https://www.kleinezeitung.at/autor/slug"))


def test_validate_author_raises_on_missing_meta():
    from scraper.schema import empty_author, validate_author
    a = empty_author("slug", "Name", "https://www.kleinezeitung.at/autor/slug")
    del a["meta"]
    with pytest.raises(ValueError, match="meta"):
        validate_author(a)


def test_validate_author_raises_on_missing_slug():
    from scraper.schema import empty_author, validate_author
    a = empty_author("slug", "Name", "https://www.kleinezeitung.at/autor/slug")
    del a["meta"]["slug"]
    with pytest.raises(ValueError, match="slug"):
        validate_author(a)


def test_validate_author_raises_on_missing_name():
    from scraper.schema import empty_author, validate_author
    a = empty_author("slug", "Name", "https://www.kleinezeitung.at/autor/slug")
    del a["profile"]["name"]
    with pytest.raises(ValueError, match="name"):
        validate_author(a)
