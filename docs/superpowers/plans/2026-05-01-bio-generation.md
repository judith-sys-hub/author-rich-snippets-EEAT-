# Bio Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `generate` pipeline stage that calls the Claude API to produce E-E-A-T German author bios and beat labels, stored in each author JSON as `profile.bio_generated` and `expertise.beats`.

**Architecture:** One new module `scraper/generate.py` owns all Claude API logic. `pipeline.py` gains a `run_generate()` function and `--stage generate` CLI option. The Anthropic client is instantiated once per run and passed into `generate_bio()`. The system prompt is marked with `cache_control` so it is cached after the first call.

**Tech Stack:** `anthropic>=0.25`, `pytest`, existing `python-dotenv`, `scraper/state.py` (unchanged)

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `requirements.txt` | Add `anthropic>=0.25` |
| Modify | `.env.example` | Add `ANTHROPIC_API_KEY` |
| Create | `scraper/generate.py` | `build_prompt()`, `generate_bio()`, `SYSTEM_PROMPT` constant |
| Create | `tests/test_generate.py` | Unit tests for both functions |
| Modify | `pipeline.py` | Add `run_generate()`, wire `--stage generate` |

---

## Task 1: Add `anthropic` dependency

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Add `anthropic` to `requirements.txt`**

The file currently reads:
```
playwright>=1.44
httpx>=0.27
beautifulsoup4>=4.12
lxml>=5.0
python-dotenv>=1.0
pytest>=8.0
```

Add one line so it reads:
```
playwright>=1.44
httpx>=0.27
beautifulsoup4>=4.12
lxml>=5.0
python-dotenv>=1.0
pytest>=8.0
anthropic>=0.25
```

- [ ] **Step 2: Add `ANTHROPIC_API_KEY` to `.env.example`**

Append to the bottom of `.env.example`:
```
ANTHROPIC_API_KEY=your_anthropic_api_key
```

- [ ] **Step 3: Install the package**

Run: `pip install anthropic`
Expected: `Successfully installed anthropic-...`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: add anthropic dependency for bio generation"
```

---

## Task 2: Implement `build_prompt()` with TDD

**Files:**
- Create: `scraper/generate.py`
- Create: `tests/test_generate.py`

- [ ] **Step 1: Create `tests/test_generate.py` with failing tests for `build_prompt()`**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/test_generate.py -v`
Expected: `ModuleNotFoundError: No module named 'scraper.generate'`

- [ ] **Step 3: Create `scraper/generate.py` with `build_prompt()` and `generate_bio()`**

```python
import json
import os
import re

import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "Du bist ein erfahrener Biografieautor für österreichische Qualitätsjournalisten.\n"
    "Deine Aufgabe: Schreibe eine E-E-A-T-optimierte Autorenbiografie auf Deutsch.\n\n"
    "Regeln:\n"
    "- 80–120 Wörter, dritte Person, professionell aber persönlich\n"
    "- Nenne Fachgebiet/Beat explizit, basierend auf den Artikeln\n"
    "- Verwende ausschließlich Fakten aus den bereitgestellten Daten\n"
    "- Keine Erfindungen, keine nicht belegten Aussagen\n\n"
    'Antworte ausschließlich als JSON:\n{"bio": "...", "beats": ["...", "..."]}'
)


def build_prompt(author_data: dict) -> str:
    profile = author_data["profile"]
    lines = [f"Name: {profile['name']}"]

    if profile.get("title"):
        lines.append(f"Jobtitel: {profile['title']}")

    if profile.get("bio_existing"):
        lines.append(f"\nBestehende Biografie:\n{profile['bio_existing']}")

    articles = author_data.get("articles", [])[:10]
    if articles:
        lines.append("\nArtikel (neueste zuerst):")
        for a in articles:
            section = f" [{a['section']}]" if a.get("section") else ""
            lines.append(f"- {a['title']}{section} ({a['published_at'][:7]})")

    awards = [
        a["title"]
        for a in author_data.get("enrichment", {}).get("awards", [])
        if a.get("title")
    ]
    if awards:
        lines.append("\nErwähnungen in Fachmedien:")
        for title in awards[:3]:
            lines.append(f"- {title}")

    return "\n".join(lines)


def generate_bio(
    author_data: dict,
    client: anthropic.Anthropic,
    system_prompt: str,
) -> dict:
    prompt = build_prompt(author_data)
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            result = json.loads(m.group())
        else:
            raise ValueError(f"Could not parse JSON from response: {raw[:200]}")

    author_data["profile"]["bio_generated"] = result.get("bio")
    author_data["expertise"]["beats"] = result.get("beats", [])
    author_data["expertise"]["derived_from_articles"] = True
    return author_data
```

- [ ] **Step 4: Run `build_prompt` tests — all should pass**

Run: `pytest tests/test_generate.py -k "build_prompt" -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add scraper/generate.py tests/test_generate.py
git commit -m "feat: add build_prompt() for bio generation prompt assembly"
```

---

## Task 3: Test `generate_bio()` with TDD

**Files:**
- Modify: `tests/test_generate.py` (append tests)

- [ ] **Step 1: Append `generate_bio` tests to `tests/test_generate.py`**

Add these tests at the bottom of the file:

```python
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
```

- [ ] **Step 2: Run all tests in `tests/test_generate.py`**

Run: `pytest tests/test_generate.py -v`
Expected: 14 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_generate.py
git commit -m "test: add generate_bio() unit tests with mock Claude client"
```

---

## Task 4: Wire `run_generate()` into `pipeline.py`

**Files:**
- Modify: `pipeline.py`

- [ ] **Step 1: Add `import os` to `pipeline.py`**

The top of `pipeline.py` currently has:
```python
import argparse
import json
import sys
```

Change it to:
```python
import argparse
import json
import os
import sys
```

- [ ] **Step 2: Add `run_generate()` after `run_enrich()` in `pipeline.py`**

Insert this function between `run_enrich()` and `main()`:

```python
def run_generate(dry_run: bool, limit: int | None) -> None:
    import time
    from scraper.generate import SYSTEM_PROMPT, generate_bio
    from scraper.state import get_authors_by_stage, update_stage

    candidates = list(get_authors_by_stage("enriched"))
    if limit:
        candidates = candidates[:limit]
    print(f"[generate] Verarbeite {len(candidates)} Autoren ...")

    if dry_run:
        for row in candidates:
            print(f"[generate] Würde generieren: {row['slug']}")
        return

    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    delay = float(os.environ.get("SCRAPE_DELAY_SECONDS", "2"))

    for row in candidates:
        slug = row["slug"]
        out_path = DATA_DIR / f"{slug}.json"
        try:
            data = json.loads(out_path.read_text(encoding="utf-8"))
            data = generate_bio(data, client, SYSTEM_PROMPT)
            out_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            update_stage(slug, "generated")
            print(f"[generate] OK: {slug}")
        except Exception as exc:
            update_stage(slug, "failed", error=str(exc))
            print(f"[generate] FEHLER: {slug} — {exc}", file=sys.stderr)
        time.sleep(delay)
```

- [ ] **Step 3: Update `--stage` choices in `main()`**

Find:
```python
    parser.add_argument("--stage", choices=["discover", "scrape", "enrich"],
```

Replace with:
```python
    parser.add_argument("--stage", choices=["discover", "scrape", "enrich", "generate"],
```

- [ ] **Step 4: Add the generate call at the bottom of `main()`**

Find:
```python
        if args.stage in (None, "enrich"):
            run_enrich(args.dry_run, args.limit)
```

Add immediately after:
```python
        if args.stage in (None, "generate"):
            run_generate(args.dry_run, args.limit)
```

- [ ] **Step 5: Run the full test suite to confirm nothing broke**

Run: `pytest --ignore=tests/test_auth.py -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add pipeline.py
git commit -m "feat: add --stage generate to pipeline (bio generation via Claude API)"
```

---

## Task 5: Smoke test with real API

- [ ] **Step 1: Add `ANTHROPIC_API_KEY` to your `.env` file**

Open `.env` and add your key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 2: Run generate on one author**

Run: `python pipeline.py --stage generate --limit 1`

Expected:
```
[generate] Verarbeite 1 Autoren ...
[generate] OK: anna-maria-aichholzer
```

- [ ] **Step 3: Verify the output JSON**

```powershell
python -c "import json; d=json.load(open('data/authors/anna-maria-aichholzer.json', encoding='utf-8')); print(d['profile']['bio_generated']); print(d['expertise']['beats'])"
```

Expected: a German paragraph of ~80–120 words and a list like `['Social Media', 'Graz-Lokales']`

- [ ] **Step 4: Verify DB stage**

Run: `python summary.py`
Expected: `generated: 1` appears in output

- [ ] **Step 5: Commit sample output**

```bash
git add data/authors/anna-maria-aichholzer.json
git commit -m "feat: smoke test — first generated bio (anna-maria-aichholzer)"
```

---

## Done

Run all 231 authors with:
```powershell
python pipeline.py --stage generate
```

State machine: `discovered → scraped → enriched → generated`
