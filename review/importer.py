import csv
import json
from pathlib import Path

from review import BEAT_COLS

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
RICHSNIPPET_DIR = Path(__file__).parent.parent / "richsnippet"
CSV_PATH = Path(__file__).parent / "author_review.csv"


def parse_beats(row: dict) -> list[str]:
    return [row[col].strip() for col in BEAT_COLS if row.get(col, "").strip()]


def import_authors(
    csv_path: Path = CSV_PATH,
    data_dir: Path = DATA_DIR,
    richsnippet_dir: Path = RICHSNIPPET_DIR,
) -> dict:
    from scraper.render import render_jsonld
    from scraper.state import update_stage

    counts = {"approved": 0, "flagged": 0, "pending": 0}
    flagged = []

    with csv_path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        status = row["status"].strip().lower()
        slug = row["slug"].strip()

        if status == "flagged":
            counts["flagged"] += 1
            flagged.append(slug)
            continue
        if status != "approved":
            counts["pending"] += 1
            continue

        counts["approved"] += 1
        json_path = data_dir / f"{slug}.json"
        if not json_path.exists():
            print(f"[import] FEHLER: {json_path.name} nicht gefunden – uebersprungen")
            continue
        author_data = json.loads(json_path.read_text(encoding="utf-8"))

        new_bio = row["bio"].strip()
        new_beats = parse_beats(row)
        current_bio = author_data["profile"].get("bio_generated") or ""
        current_beats = (author_data.get("expertise") or {}).get("beats") or []

        try:
            if new_bio != current_bio or new_beats != current_beats:
                author_data["profile"]["bio_generated"] = new_bio
                if author_data.get("expertise") is None:
                    author_data["expertise"] = {"beats": [], "derived_from_articles": False}
                author_data["expertise"]["beats"] = new_beats
                json_path.write_text(
                    json.dumps(author_data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                jsonld = render_jsonld(author_data)
                (richsnippet_dir / f"{slug}.json").write_text(
                    json.dumps(jsonld, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"[import] OK (aktualisiert): {slug}")
            else:
                print(f"[import] OK (unveraendert): {slug}")
            update_stage(slug, "reviewed")
        except Exception as exc:
            print(f"[import] FEHLER: {slug} – {exc}")

    for slug in flagged:
        print(f"[import] FLAGGED (uebersprungen): {slug}")

    print(
        f"[import] {counts['approved']} reviewed, "
        f"{counts['flagged']} flagged zum Nachbearbeiten"
    )
    return counts


if __name__ == "__main__":
    import_authors()