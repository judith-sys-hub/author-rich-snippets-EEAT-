# Sub-project 3: Rich Snippet Output — Design Spec

**Goal:** Generate JSON-LD Rich Snippets (Schema.org `Person` + `NewsArticle`) for each of the 231 kleinezeitung.at authors, as standalone files suitable for embedding in CMS CUE by Stibo.

**Date:** 2026-05-01

---

## Decisions

| Question | Decision |
|---|---|
| Output format | One file per author: `richsnippet/{slug}.json` |
| Markup type | JSON-LD only (no HTML Microdata) |
| Schema.org types | `Person` + `NewsArticle` references |
| Pipeline integration | New `render` stage in `pipeline.py` |
| JSON-LD structure | `@graph` with flat Person + NewsArticle nodes |

---

## Architecture

A new module `scraper/render.py` contains a single pure function `render_jsonld(author_data: dict) -> dict`. It has no file I/O — accepts author data, returns a JSON-LD dict. This makes it trivially testable.

`pipeline.py` adds `run_render()`, which reads all `generated` authors from the DB, calls `render_jsonld()` for each, and writes `richsnippet/{slug}.json`. Output directory is created automatically.

```
pipeline.py
  └── run_render()
        └── scraper/render.py → render_jsonld(author_data) → dict
              └── writes to richsnippet/{slug}.json
```

State machine extension: `generated → rendered` (or `failed` on error). Re-running is safe — files are overwritten.

No new dependencies. Pure Python stdlib (`json`, `pathlib`).

---

## JSON-LD Schema

Each output file contains a single JSON object with `@context` and `@graph`.

### Person node

`@id` is set to `profile_url` (the canonical author page URI).

Fields included (null/empty fields are omitted):

| JSON-LD field | Source |
|---|---|
| `@type` | `"Person"` |
| `@id` | `profile.profile_url` |
| `name` | `profile.name` |
| `jobTitle` | `profile.title` |
| `description` | `profile.bio_generated` |
| `image` | `profile.photo_url` |
| `url` | `profile.profile_url` |
| `knowsAbout` | `expertise.beats` (array) |
| `worksFor` | Fixed: `NewsMediaOrganization` for Kleine Zeitung |
| `sameAs` | Non-null values from `enrichment.social_links` + `enrichment.wikipedia_url` |

`worksFor` is always:
```json
{
  "@type": "NewsMediaOrganization",
  "@id": "https://www.kleinezeitung.at",
  "name": "Kleine Zeitung"
}
```

### NewsArticle nodes

One node per article in `articles[]` (up to 15, the full scraped set). Fields:

| JSON-LD field | Source |
|---|---|
| `@type` | `"NewsArticle"` |
| `headline` | `article.title` |
| `url` | `article.url` |
| `datePublished` | `article.published_at` (ISO date string) |
| `articleSection` | `article.section` (omitted if null/empty) |
| `author` | `{"@id": "<profile_url>"}` — back-reference to Person |
| `publisher` | Same `NewsMediaOrganization` as `worksFor` |

### Example output

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Person",
      "@id": "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer",
      "name": "Anna-Maria Aichholzer",
      "jobTitle": "Redakteurin News & Social Media",
      "description": "Anna-Maria Aichholzer ist Redakteurin fuer News & Social Media ...",
      "image": "https://img.kleinezeitung.at/...",
      "url": "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer",
      "knowsAbout": ["Gesellschaft & Lokales Graz", "Popkultur & Entertainment", "Social Media & News"],
      "worksFor": {
        "@type": "NewsMediaOrganization",
        "@id": "https://www.kleinezeitung.at",
        "name": "Kleine Zeitung"
      },
      "sameAs": ["https://www.instagram.com/anna.aichholzer"]
    },
    {
      "@type": "NewsArticle",
      "headline": "Grazer Seniorinnen haengten Schals und Hauben fuer obdachlose Menschen auf Baeumen auf",
      "url": "https://www.kleinezeitung.at/artikel/20372411/...",
      "datePublished": "2025-12-09",
      "articleSection": "Zur freien Entnahme",
      "author": {"@id": "https://www.kleinezeitung.at/autor/891/anna-maria-aichholzer"},
      "publisher": {
        "@type": "NewsMediaOrganization",
        "@id": "https://www.kleinezeitung.at",
        "name": "Kleine Zeitung"
      }
    }
  ]
}
```

---

## Pipeline Integration

### New files

- `scraper/render.py` — pure `render_jsonld(author_data) -> dict` function
- `tests/test_render.py` — unit tests
- `richsnippet/` — output directory (gitignored, parallel to `data/`)

### Modified files

- `pipeline.py` — add `RICHSNIPPET_DIR`, `run_render()`, extend `--stage` choices
- `scraper/state.py` — no changes needed (`update_stage` and `get_authors_by_stage` already generic)

### CLI

```
python pipeline.py                     # full pipeline (all stages)
python pipeline.py --stage render      # render only
python pipeline.py --stage render --limit 3   # smoke test
```

---

## Testing

Unit tests in `tests/test_render.py` cover:

- Person node: all fields present when data is complete
- Person node: null fields are omitted (photo_url=None -> no `image` key)
- Person node: empty beats -> `knowsAbout` omitted
- Person node: `sameAs` contains only non-null social links
- Person node: `sameAs` omitted when all social links are null and no wikipedia
- NewsArticle nodes: correct count (one per article)
- NewsArticle: `articleSection` omitted when null
- NewsArticle: `author` correctly back-references Person `@id`
- `@graph` structure: correct `@context`, `@graph` key present
- Integration: full author fixture produces valid output structure