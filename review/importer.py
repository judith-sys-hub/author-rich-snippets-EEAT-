import json
from pathlib import Path

import openpyxl

DATA_DIR = Path(__file__).parent.parent / "data" / "authors"
RICHSNIPPET_DIR = Path(__file__).parent.parent / "richsnippet"
XLSX_PATH = Path(__file__).parent / "author_review.xlsx"


def parse_beats_from_themen(themen: str) -> list[str]:
    if not themen or not themen.strip():
        return []
    return [b.strip() for b in themen.split(";") if b.strip()]


def read_xlsx(xlsx_path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = []
    for row_vals in ws.iter_rows(min_row=3, values_only=True):
        padded = list(row_vals) + [None] * 5
        slug, name, status, bio, themen = padded[:5]
        if not slug:
            continue
        rows.append({
            "slug": str(slug).strip(),
            "name": str(name or ""),
            "status": str(status or "").strip().lower(),
            "bio": str(bio or "").strip(),
            "themen": str(themen or "").strip(),
        })
    return rows


def import_authors(
    xlsx_path: Path = XLSX_PATH,
    data_dir: Path = DATA_DIR,
    richsnippet_dir: Path = RICHSNIPPET_DIR,
) -> dict:
    from scraper.render import render_jsonld
    from scraper.state import update_stage

    counts = {"approved": 0, "flagged": 0, "pending": 0}
    flagged = []

    rows = read_xlsx(xlsx_path)

    for row in rows:
        status = row["status"]
        slug = row["slug"]

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

        new_bio = row["bio"]
        new_beats = parse_beats_from_themen(row["themen"])
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
        except Exception as exc:
            print(f"[import] FEHLER: {slug} – {exc}")
            continue
        update_stage(slug, "reviewed")

    for slug in flagged:
        print(f"[import] FLAGGED (uebersprungen): {slug}")

    print(
        f"[import] {counts['approved']} reviewed, "
        f"{counts['flagged']} flagged zum Nachbearbeiten"
    )
    return counts


if __name__ == "__main__":
    import_authors()
