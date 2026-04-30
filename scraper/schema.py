from datetime import datetime, timezone


def empty_author(slug: str, name: str, profile_url: str) -> dict:
    return {
        "meta": {
            "slug": slug,
            "last_scraped": datetime.now(timezone.utc).isoformat(),
            "scrape_version": 1,
        },
        "profile": {
            "name": name,
            "title": None,
            "department": None,
            "bio_existing": None,
            "profile_url": profile_url,
            "photo_url": None,
        },
        "expertise": {
            "beats": [],
            "derived_from_articles": False,
        },
        "articles": [],
        "enrichment": {
            "awards": [],
            "social_links": {
                "linkedin": None,
                "bluesky": None,
                "twitter": None,
                "instagram": None,
            },
            "wikipedia_url": None,
            "enrichment_sources": [],
        },
    }


def validate_author(data: dict) -> None:
    if "meta" not in data:
        raise ValueError("missing field: meta")
    for field in ("slug", "last_scraped", "scrape_version"):
        if field not in data["meta"]:
            raise ValueError(f"missing field: meta.{field}")
    if "profile" not in data:
        raise ValueError("missing field: profile")
    for field in ("name", "profile_url"):
        if field not in data["profile"]:
            raise ValueError(f"missing field: profile.{field}")
