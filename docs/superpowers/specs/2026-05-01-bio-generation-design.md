# Sub-project 2: Bio Generation — Design Spec

**Date:** 2026-05-01
**Status:** Approved
**Pipeline stage:** `generate` (after `enrich`)

## Goal

Generate E-E-A-T-optimised German author bios (~80–120 words) for all 231 enriched
kleinezeitung.at authors. Output is a draft for editorial review (Sub-project 4), not
published automatically. Beat extraction is a byproduct of the same Claude call.

## Architecture

One new module: `scraper/generate.py`

| Function | Responsibility |
|---|---|
| `build_prompt(author_data)` | Assembles per-author user message |
| `generate_bio(author_data, client, system_prompt)` | Calls Claude API, parses response, returns updated author dict |

The Anthropic client is instantiated once in `pipeline.py` and passed into
`generate_bio` — not re-created per author.

The system prompt is marked with `cache_control` so it is cached after the first
call and charged at 10% on subsequent calls (~60–70% total cost reduction vs.
no caching).

## Prompt Design

### System prompt (cached)

```
Du bist ein erfahrener Biografieautor für österreichische Qualitätsjournalisten.
Deine Aufgabe: Schreibe eine E-E-A-T-optimierte Autorenbiografie auf Deutsch.

Regeln:
- 80–120 Wörter, dritte Person, professionell aber persönlich
- Nenne Fachgebiet/Beat explizit, basierend auf den Artikeln
- Verwende ausschließlich Fakten aus den bereitgestellten Daten
- Keine Erfindungen, keine nicht belegten Aussagen

Antworte ausschließlich als JSON:
{"bio": "...", "beats": ["...", "..."]}
```

### Per-author user message (not cached)

- Name + Jobtitel
- `bio_existing` (omitted if null — Claude generates purely from article evidence)
- Up to 10 most recent article titles + section (Ressort)
- Award titles and enrichment sources if present

### Response format

```json
{"bio": "...", "beats": ["Social Media", "Popkultur", "Graz-Lokales"]}
```

- `bio` → written to `profile.bio_generated`
- `beats` → written to `expertise.beats`; `expertise.derived_from_articles` set to `true`

If `json.loads()` fails, the author is marked `failed` in the DB with the error
message and the pipeline continues.

## Output Fields

| Field | Type | Description |
|---|---|---|
| `profile.bio_generated` | string | Generated bio draft (80–120 words, German) |
| `expertise.beats` | list[str] | 2–4 topic labels derived from articles |
| `expertise.derived_from_articles` | bool | Set to `true` after generation |

`profile.bio_existing` is preserved unchanged — editors can compare both.

## Pipeline Integration

```
discover → scrape → enrich → generate
```

- `python pipeline.py` runs all four stages
- `python pipeline.py --stage generate` reruns only bio generation (useful when
  updating the prompt and regenerating without re-scraping)
- `--limit N` works the same as other stages
- Rate limiting: reuses `SCRAPE_DELAY_SECONDS` between API calls

### State machine

| Previous stage | After success | After failure |
|---|---|---|
| `enriched` | `generated` | `failed` |

### Environment

`ANTHROPIC_API_KEY` added to `.env.example`.

## Cost estimate

- 231 authors × ~1,000 input tokens + ~250 output tokens
- System prompt (~600 tokens) cached after first call: ~10% cost on subsequent calls
- Model: `claude-sonnet-4-6`
- Estimated total: **~$1–2**

## Error handling

- API failure or malformed JSON response → mark author `failed`, log error, continue
- Missing `bio_existing` → omit from prompt, generate from articles only
- Empty articles list → still attempt generation from name/title alone

## Out of scope

- Editorial review UI (Sub-project 4)
- CMS write-back to CUE (Sub-project 3)
- Bio translation or multi-language support
