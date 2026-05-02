import csv
import json
from pathlib import Path

from review import BEAT_COLS, FIELDNAMES

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
CSV_PATH = Path(__file__).parent / "author_review.csv"


def build_row(author_data: dict) -> dict:
    profile = author_data["profile"]
    beats = (author_data.get("expertise") or {}).get("beats") or []
    if len(beats) > len(BEAT_COLS):
        print(f"[export] WARNUNG: {author_data['meta']['slug']} hat {len(beats)} Beats, nur {len(BEAT_COLS)} werden exportiert")
    row = {
        "slug": author_data["meta"]["slug"],
        "name": profile.get("name", ""),
        "status": "pending",
        "bio": profile.get("bio_generated") or "",
    }
    for i, col in enumerate(BEAT_COLS):
        row[col] = beats[i] if i < len(beats) else ""
    return row


def export_authors(data_dir: Path = DATA_DIR, csv_path: Path = CSV_PATH) -> int:
    from scraper.state import get_authors_by_stage

    candidates = list(get_authors_by_stage("rendered"))
    rows = []
    for row in candidates:
        slug = row["slug"]
        json_path = data_dir / f"{slug}.json"
        if not json_path.exists():
            print(f"[export] WARNUNG: {json_path.name} nicht gefunden – uebersprungen")
            continue
        author_data = json.loads(json_path.read_text(encoding="utf-8"))
        try:
            rows.append(build_row(author_data))
        except Exception as exc:
            raise RuntimeError(f"Fehler bei {slug}: {exc}") from exc

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(csv_path)

    return len(rows)


if __name__ == "__main__":
    count = export_authors()
    print(f"[export] {count} Autoren exportiert -> {CSV_PATH}")