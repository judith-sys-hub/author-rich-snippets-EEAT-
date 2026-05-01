import json
import re

import anthropic

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "Du bist ein erfahrener Biografieautor fÃ¼r Ã¶sterreichische QualitÃ¤tsjournalisten.\n"
    "Deine Aufgabe: Schreibe eine E-E-A-T-optimierte Autorenbiografie auf Deutsch.\n\n"
    "Regeln:\n"
    "- 80â€“120 WÃ¶rter, dritte Person, professionell aber persÃ¶nlich\n"
    "- Nenne Fachgebiet/Beat explizit, basierend auf den Artikeln\n"
    "- Verwende ausschlieÃŸlich Fakten aus den bereitgestellten Daten\n"
    "- Keine Erfindungen, keine nicht belegten Aussagen\n\n"
    'Antworte ausschlieÃŸlich als JSON:\n{"bio": "...", "beats": ["...", "..."]}'
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
        lines.append("\nErwÃ¤hnungen in Fachmedien:")
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

