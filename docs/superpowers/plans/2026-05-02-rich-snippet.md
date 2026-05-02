# Rich Snippet Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `render` stage to the pipeline that generates a `richsnippet/{slug}.json` JSON-LD file for each of the 231 generated authors using Schema.org `Person` + `NewsArticle` nodes in an `@graph` structure.

**Architecture:** A pure function `render_jsonld(author_data) -> dict` in `scraper/render.py` handles all JSON-LD construction with no file I/O. `pipeline.py` gets a `run_render()` orchestrator that reads `generated` authors from the DB, calls `render_jsonld()` for each, and writes to `richsnippet/{slug}.json`. State transitions from `generated` to `rendered`.

**Tech Stack:** Python 3.14, pytest, stdlib only (`json`, `pathlib`) — no new dependencies.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `scraper/render.py` | CREATE | Pure `render_jsonld(author_data: dict) -> dict` function |
| `tests/test_render.py` | CREATE | Unit tests for `render_jsonld` (23 tests) |
| `tests/test_pipeline_render.py` | CREATE | Integration tests for `run_render()` in pipeline.py |
| `pipeline.py` | MODIFY | Add `RICHSNIPPET_DIR`, `run_render()`, extend `--stage` choices |
| `.gitignore` | MODIFY | Add `richsnippet/` output directory |

---

### Task 1: `scraper/render.py` — core JSON-LD render function

**Files:**
- Create: `scraper/render.py`
- Create: `tests/test_render.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_render.py` with the following content:

```python
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
    assert pub["name"] == "Kleine Zeitung"


def test_no_articles_produces_only_person(full_author):
    full_author["articles"] = []
    result = render_jsonld(full_author)
    assert len(result["@graph"]) == 1
    assert result["@graph"][0]["@type"] == "Person"
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_render.py -v
```

Expected: all 23 tests FAIL with `ModuleNotFoundError: No module named 'scraper.render'`

- [ ] **Step 3: Create `scraper/render.py`**

```python
_PUBLISHER = {
    "@type": "NewsMediaOrganization",
    "@id": "https://www.kleinezeitung.at",
    "name": "Kleine Zeitung",
}


def _set_if(node: dict, key: str, value) -> None:
    if value:
        node[key] = value


def render_jsonld(author_data: dict) -> dict:
    profile = author_data["profile"]
    profile_url = profile["profile_url"]

    person: dict = {"@type": "Person", "@id": profile_url}
    _set_if(person, "name", profile.get("name"))
    _set_if(person, "jobTitle", profile.get("title"))
    _set_if(person, "description", profile.get("bio_generated"))
    _set_if(person, "image", profile.get("photo_url"))
    person["url"] = profile_url
    person["worksFor"] = _PUBLISHER

    beats = (author_data.get("expertise") or {}).get("beats") or []
    if beats:
        person["knowsAbout"] = beats

    enrichment = author_data.get("enrichment") or {}
    social = enrichment.get("social_links") or {}
    same_as = [v for v in social.values() if v]
    wiki = enrichment.get("wikipedia_url")
    if wiki:
        same_as.append(wiki)
    if same_as:
        person["sameAs"] = same_as

    graph: list = [person]
    for article in author_data.get("articles") or []:
        node: dict = {
            "@type": "NewsArticle",
            "headline": article["title"],
            "url": article["url"],
            "datePublished": article["published_at"],
            "author": {"@id": profile_url},
            "publisher": _PUBLISHER,
        }
        if article.get("section"):
            node["articleSection"] = article["section"]
        graph.append(node)

    return {"@context": "https://schema.org", "@graph": graph}
```

- [ ] **Step 4: Run tests — verify they pass**

```
pytest tests/test_render.py -v
```

Expected: all 23 tests PASS

- [ ] **Step 5: Commit**

```
git add scraper/render.py tests/test_render.py
git commit -m "feat: add render_jsonld for Schema.org Person+NewsArticle JSON-LD output"
```

---

### Task 2: `pipeline.py` — render stage integration

**Files:**
- Create: `tests/test_pipeline_render.py`
- Modify: `pipeline.py` (lines 13–14, after line 131, line 142, after line 164)
- Modify: `.gitignore`

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_pipeline_render.py`:

```python
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
        with patch("scraper.state.update_stage"):
            pipeline.run_render(dry_run=False, limit=None)

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
```

- [ ] **Step 2: Run test — verify it fails**

```
pytest tests/test_pipeline_render.py -v
```

Expected: FAIL with `AttributeError: module 'pipeline' has no attribute 'run_render'`

- [ ] **Step 3: Add `RICHSNIPPET_DIR` to `pipeline.py`**

After line 14 (`DATA_DIR.mkdir(parents=True, exist_ok=True)`), insert:

```python
RICHSNIPPET_DIR = Path(__file__).parent / "richsnippet"
RICHSNIPPET_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Add `run_render()` to `pipeline.py`**

After the `run_generate()` function (after line 131, `time.sleep(delay)`), insert:

```python

def run_render(dry_run: bool, limit: int | None) -> None:
    from scraper.render import render_jsonld
    from scraper.state import get_authors_by_stage, update_stage

    candidates = list(get_authors_by_stage("generated"))
    if limit:
        candidates = candidates[:limit]
    print(f"[render] Verarbeite {len(candidates)} Autoren ...")

    for row in candidates:
        slug = row["slug"]
        out_path = DATA_DIR / f"{slug}.json"
        richsnippet_path = RICHSNIPPET_DIR / f"{slug}.json"
        if dry_run:
            print(f"[render] Würde rendern: {slug}")
            continue
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            jsonld = render_jsonld(data)
            richsnippet_path.write_text(
                json.dumps(jsonld, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            update_stage(slug, "rendered")
            print(f"[render] OK: {slug}")
        except Exception as exc:
            update_stage(slug, "failed", error=str(exc))
            print(f"[render] FEHLER: {slug} — {exc}", file=sys.stderr)
```

- [ ] **Step 5: Extend `--stage` choices**

On line 142, change:

```python
    parser.add_argument("--stage", choices=["discover", "scrape", "enrich", "generate"],
                        default=None, help="Nur eine Stage ausführen")
```

to:

```python
    parser.add_argument("--stage", choices=["discover", "scrape", "enrich", "generate", "render"],
                        default=None, help="Nur eine Stage ausführen")
```

- [ ] **Step 6: Add render stage call in `main()`**

After line 164 (`run_generate(args.dry_run, args.limit)`), insert:

```python
        if args.stage in (None, "render"):
            run_render(args.dry_run, args.limit)
```

- [ ] **Step 7: Run tests — verify they pass**

```
pytest tests/test_pipeline_render.py -v
```

Expected: both tests PASS

- [ ] **Step 8: Run the full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS (no regressions)

- [ ] **Step 9: Add `richsnippet/` to `.gitignore`**

Append to `.gitignore`:

```
richsnippet/
```

- [ ] **Step 10: Smoke test against real data**

```
python pipeline.py --stage render --limit 3
```

Expected output:
```
[render] Verarbeite 3 Autoren ...
[render] OK: <slug-1>
[render] OK: <slug-2>
[render] OK: <slug-3>
```

Verify one output file is valid JSON-LD:

```
python -c "import json; d=json.load(open('richsnippet/<slug-1>.json', encoding='utf-8')); print(d['@context'], len(d['@graph']), 'nodes')"
```

Expected: `https://schema.org 16 nodes` (1 Person + up to 15 articles)

- [ ] **Step 11: Commit**

```
git add pipeline.py tests/test_pipeline_render.py .gitignore
git commit -m "feat: add render stage to pipeline — generates JSON-LD rich snippets per author"
```