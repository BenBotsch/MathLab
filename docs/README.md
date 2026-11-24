# Dokumentation

MathLab ist ein agentisches System für mathematische Forschung und Beweisführung. Sprachmodelle schlagen Beweisschritte, Strategien und Vermutungen vor. Über ihre Gültigkeit entscheidet ein formaler Prüfer wie Lean 4. Die Implementierung hat mit dem Python-Grundgerüst begonnen. Dieses Verzeichnis enthält die Konzepte, das Backlog und die Entscheidungen.

## Inhalt

| Pfad | Inhalt |
| --- | --- |
| [research/](research/) | Unveränderte Konzeptdokumente. ARCH ist das [Forschungs- und Architekturkonzept](research/Mathematisches_Beweissystem_Forschungs_und_Architekturkonzept.md), UI das [Konzept für das Research Control Center](research/Mathematisches_Beweissystem_UI_Research_Control_Center.md). |
| [glossary.md](glossary.md) | Begriffe und die getrennten Statusräume für Erkenntnisstufe, Verifikation, Agenten und Beweisknoten |
| [backlog/BACKLOG.md](backlog/BACKLOG.md) | Statusübersicht aller Epics und Features mit den Abschnitten Now, Next und Later |
| [backlog/ROADMAP.md](backlog/ROADMAP.md) | Meilensteine M1 bis M6 mit Exit-Kriterien und der Reihenfolge in M1 |
| [backlog/WORKFLOW.md](backlog/WORKFLOW.md) | Status, Definition of Ready und Done, Ablauf für Agenten und fachliche Invarianten |
| [backlog/TRACEABILITY.md](backlog/TRACEABILITY.md) | Zuordnung jedes Quellabschnitts zu Features |
| [backlog/epics/](backlog/epics/) | Ein Dokument pro Epic, die Features stehen als Abschnitte darin |
| [backlog/templates/](backlog/templates/) | Vorlage für neue Epics |
| [decisions/](decisions/) | ADR-Verfahren, ADR-Vorlage und [offene Entscheidungen](decisions/OPEN_DECISIONS.md) |

## Entwicklung

Voraussetzung ist [uv](https://docs.astral.sh/uv/). Die Python-Version steht in `.python-version`, die Werkzeuge legt [ADR-0005](decisions/adr-0005-repository-layout.md) fest. Im Repository-Wurzelverzeichnis:

```text
uv sync
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

### Container

Voraussetzung ist Docker (unter Windows Docker Desktop). Backend und Datenbank startet ein Befehl:

```text
docker compose up -d --build
```

Das Backend ist bis F-14.01 ein Platzhalter. Es prüft die Datenbankverbindung und gibt den Environment-Fingerprint aus (`docker compose logs backend`). Die Lean-Engine mit Mathlib baut `docker compose --profile engines build lean`. Der erste Build lädt den Mathlib-Cache von mehreren GB. Die Lean-Version steht in `lean/lean-toolchain`, die Mathlib-Version in `lean/lakefile.toml` und `lean/lake-manifest.json`. Es wird kein Port zum Host freigegeben. Der Beispielbeweis aus ARCH §15 liegt in `lean/MathlabLean/OddSum.lean`. Die Container-Tests laufen mit `MATHLAB_TEST_LEAN_IMAGE=mathlab-lean:latest uv run pytest tests/test_lean_engine.py`. Generierter Code läuft über `mathlab.sandbox.run_sandboxed` ohne Netzwerk und mit Ressourcenlimits; die Sandbox-Tests laufen mit `MATHLAB_TEST_SANDBOX_IMAGE=python:3.12-slim uv run pytest tests/test_sandbox.py`.

Die Tests des Event Store brauchen PostgreSQL und laufen nur, wenn `MATHLAB_TEST_DATABASE_URL` gesetzt ist. Eine Wegwerf-Datenbank startet `docker run --rm -d -p 127.0.0.1:55432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust postgres:17.6-bookworm`, die Adresse ist dann `postgresql://postgres@127.0.0.1:55432/postgres`. Die Anwendung liest ihre Datenbank aus `MATHLAB_DATABASE_URL`.

## Leseweg

Für einen Überblick genügen die Abschnitte 1, 4 und 19 von ARCH und die Abschnitte 1 und 20 von UI. Danach zeigen [ROADMAP.md](backlog/ROADMAP.md) und [BACKLOG.md](backlog/BACKLOG.md), was in welcher Reihenfolge entsteht.

Wer ein Feature umsetzt, liest zuerst [AGENTS.md](../AGENTS.md) und [WORKFLOW.md](backlog/WORKFLOW.md), dann die Epic-Datei und zuletzt die im Feature genannten Quellabschnitte. Das Feature ist die Arbeitsanweisung. Die Quelle liefert den fachlichen Hintergrund.

## Quellverweise

Features verweisen mit `ARCH §x.y` und `UI §x.y` auf die Abschnitte der beiden Konzeptdokumente. Die Dateien unter [research/](research/) werden nicht bearbeitet. Ergänzungen und Abweichungen stehen in Features, ADRs oder offenen Entscheidungen.
