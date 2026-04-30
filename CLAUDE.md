# Projekt-Kontext: Autorenprofile Kleine Zeitung

## Auftraggeber
kleinezeitung.at — österreichisches Traditionsmedienhaus mit Sitz in Graz.

## Sprache
Alle Inhalte **ausschließlich auf Deutsch**. Englisch nur in technischen Codekommentaren und JSON-Keys.

## Faktentreue & Quellen
- Alle inhaltlichen Aussagen müssen quellenbasiert und belegbar sein.
- Jede Aussage, die nicht direkt aus kleinezeitung.at oder einer offiziellen Quelle stammt, muss mit einem Link zitiert werden.
- Informationen aus externen Quellen (Horizont.at, derstandard.at/Etat, Wikipedia.org/de, LinkedIn, Bluesky, Twitter/X, Instagram) sind mit dem Vermerk **„Zu verifizieren"** zu kennzeichnen.

## Sicherheitsrichtlinien
- Keine hartcodierten API-Keys, Passwörter oder Zugangsdaten im Code oder in Markdown-Dateien.
- Secrets ausschließlich über Umgebungsvariablen (`.env`, nie in Git committen).
- `.env`-Dateien in `.gitignore` aufnehmen.
- Keine personenbezogenen Daten (E-Mail-Adressen, Telefonnummern) in öffentlichen Repositories speichern.
- Alle externen HTTP-Requests über HTTPS.
- Rate-Limiting und robots.txt beim Web-Scraping respektieren.
- Keine Scraping-Aktivitäten ohne Prüfung der Nutzungsbedingungen der Zielseite.

## Scope
Nur Autor:innen, die zwischen **2025 und 2026** mindestens einen Artikel auf kleinezeitung.at veröffentlicht haben (aktive Redaktion). Ältere oder inaktive Profile werden nicht verarbeitet.

## Ziel
Erstellung E-E-A-T-konformer Autorenprofile für alle Redakteur:innen auf kleinezeitung.at, implementierbar als Rich Snippets (JSON-LD + HTML Microdata) im CMS CUE by Stibo.

## Output-Format
- Maschinenlesbar: **JSON-LD** im `<head>` jedes Artikels (`@type: Person` / `@type: NewsArticle`)
- Menschenlesbar: **HTML** mit `itemscope`/`itemtype`-Attributen (Schema.org)
- Rohdaten: **JSON** pro Autor als Quelldatei im Repository

## Repository
Öffentliches GitHub-Repository — muss für andere Medienhäuser nachnutzbar sein.
