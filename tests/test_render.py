import pytest
from scraper.render import render_jsonld


@pytest.fixture
def full_author():
    return {
        "meta": {"slug": "anna-maria-aichholzer"},
        "profile": {
            "name": "Anna-Maria Aichholzer",
            "title": "Redakteurin News & Social Media",
            "bio_generated": "Anna-Maria Aichholzer ist Redakteurin.",
            "profile_url": "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer",
            "photo_url": "https://img.kleinezeitung.at/photo.png",
        },
        "expertise": {
            "beats": ["Gesellschaft & Lokales Graz", "Popkultur & Entertainment"],
            "derived_from_articles": True,
        },
        "articles": [
            {
                "url": "https://www.kleinezeitung.at/artikel/123/artikel-eins",
                "title": "Artikel Eins",
                "published_at": "2025-12-09",
                "section": "Graz",
            },
            {
                "url": "https://www.kleinezeitung.at/artikel/456/artikel-zwei",
                "title": "Artikel Zwei",
                "published_at": "2025-11-01",
                "section": None,
            },
        ],
        "enrichment": {
            "awards": [],
            "social_links": {
                "linkedin": None,
                "bluesky": None,
                "twitter": None,
                "instagram": "https://www.instagram.com/anna.aichholzer",
            },
            "wikipedia_url": None,
        },
    }


# --- @graph structure ---

def test_context_is_schema_org(full_author):
    result = render_jsonld(full_author)
    assert result["@context"] == "https://schema.org"


def test_graph_key_present(full_author):
    result = render_jsonld(full_author)
    assert "@graph" in result


def test_person_node_is_first(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["@type"] == "Person"


# --- Person node fields ---

def test_person_id_is_profile_url(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["@id"] == "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer"


def test_person_name(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["name"] == "Anna-Maria Aichholzer"


def test_person_job_title(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["jobTitle"] == "Redakteurin News & Social Media"


def test_person_description(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["description"] == "Anna-Maria Aichholzer ist Redakteurin."


def test_person_image(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["image"] == "https://img.kleinezeitung.at/photo.png"


def test_person_url(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["url"] == "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer"


def test_person_null_image_omitted(full_author):
    full_author["profile"]["photo_url"] = None
    result = render_jsonld(full_author)
    assert "image" not in result["@graph"][0]


def test_person_null_title_omitted(full_author):
    full_author["profile"]["title"] = None
    result = render_jsonld(full_author)
    assert "jobTitle" not in result["@graph"][0]


def test_person_works_for(full_author):
    result = render_jsonld(full_author)
    wf = result["@graph"][0]["worksFor"]
    assert wf["@type"] == "NewsMediaOrganization"
    assert wf["@id"] == "https://www.kleinezeitung.at"
    assert wf["name"] == "Kleine Zeitung"


def test_person_knows_about(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["knowsAbout"] == [
        "Gesellschaft & Lokales Graz",
        "Popkultur & Entertainment",
    ]


def test_person_empty_beats_omits_knows_about(full_author):
    full_author["expertise"]["beats"] = []
    result = render_jsonld(full_author)
    assert "knowsAbout" not in result["@graph"][0]


def test_person_same_as_non_null_only(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][0]["sameAs"] == ["https://www.instagram.com/anna.aichholzer"]


def test_person_same_as_omitted_when_all_null(full_author):
    full_author["enrichment"]["social_links"] = {
        "linkedin": None, "bluesky": None, "twitter": None, "instagram": None
    }
    full_author["enrichment"]["wikipedia_url"] = None
    result = render_jsonld(full_author)
    assert "sameAs" not in result["@graph"][0]


def test_person_wikipedia_in_same_as(full_author):
    full_author["enrichment"]["social_links"] = {
        "linkedin": None, "bluesky": None, "twitter": None, "instagram": None
    }
    full_author["enrichment"]["wikipedia_url"] = "https://de.wikipedia.org/wiki/Anna"
    result = render_jsonld(full_author)
    assert result["@graph"][0]["sameAs"] == ["https://de.wikipedia.org/wiki/Anna"]


# --- NewsArticle nodes ---

def test_article_count(full_author):
    result = render_jsonld(full_author)
    assert len(result["@graph"]) == 3  # 1 Person + 2 articles


def test_article_type(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][1]["@type"] == "NewsArticle"


def test_article_headline(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][1]["headline"] == "Artikel Eins"


def test_article_url(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][1]["url"] == "https://www.kleinezeitung.at/artikel/123/artikel-eins"


def test_article_date_published(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][1]["datePublished"] == "2025-12-09"


def test_article_section_included_when_present(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][1]["articleSection"] == "Graz"


def test_article_section_omitted_when_null(full_author):
    result = render_jsonld(full_author)
    assert "articleSection" not in result["@graph"][2]


def test_article_author_back_reference(full_author):
    result = render_jsonld(full_author)
    assert result["@graph"][1]["author"] == {
        "@id": "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer"
    }


def test_article_publisher(full_author):
    result = render_jsonld(full_author)
    pub = result["@graph"][1]["publisher"]
    assert pub["@type"] == "NewsMediaOrganization"
    assert pub["@id"] == "https://www.kleinezeitung.at"
    assert pub["name"] == "Kleine Zeitung"


def test_no_articles_produces_only_person(full_author):
    full_author["articles"] = []
    result = render_jsonld(full_author)
    assert len(result["@graph"]) == 1
    assert result["@graph"][0]["@type"] == "Person"