# E00 Projektfundament

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §3.2, §17, §18.3, §21.1, §22; UI §19
- Abhängige Epics: keine. Alle anderen Epics bauen hierauf auf.

## Ziel

Ein reproduzierbares Repository, in dem Toolchain, Abhängigkeiten und Umgebungen fixiert sind und jede Änderung durch CI-Gates läuft. Die Entscheidungen zu Plattform, Layout und Werkzeugen sind getroffen, bevor Code entsteht.

## Abgrenzung

Fachliche Sicherheitsmaßnahmen wie Sandbox und Toolrechte liegen in E24. Lean-spezifische Einrichtung liegt in E04.

## Invarianten

Versionen von Python, Lean, Mathlib, Solvern und Bibliotheken sind gepinnt (ARCH §3.2, UI §19.2). Jeder Run kann seinen Environment-Fingerprint nennen.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-00.01 | Architekturentscheidungen für M1 vorbereiten | `blocked` | P0 | M1 |
| F-00.02 | Repository-Grundgerüst | `done` | P0 | M1 |
| F-00.03 | Toolchain-Pinning und Environment-Fingerprint | `done` | P0 | M1 |
| F-00.04 | Container-Umgebung | `ready` | P0 | M1 |
| F-00.05 | CI-Grundgates | `ready` | P0 | M1 |
| F-00.06 | Fachliche CI-Gates | `todo` | P1 | M2 |
| F-00.07 | Lizenzinventar | `todo` | P1 | M1 |
| F-00.08 | Entwickler-Setup dokumentieren | `todo` | P1 | M1 |
| F-00.09 | Sicherung des Datenordners | `ready` | P1 | M1 |

## Features

### F-00.01 Architekturentscheidungen für M1 vorbereiten

- Status: `blocked` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: keine
- Quelle: ARCH §17.1, §17.3, §18.3; UI §19
- Bearbeiter: Claude (Agent) · Nachweise: ADR-0001 bis ADR-0006 in docs/decisions/. ADR-0001, 0003, 0004, 0005 und 0006 sind am 2026-11-23 vom Benutzer angenommen.

Für OD-01 bis OD-06 werden Optionen recherchiert, verglichen und als ADR-Entwurf mit Empfehlung vorgelegt. Die Entscheidung trifft der Benutzer.

- [x] Für jede OD-01 bis OD-06 liegt ein ADR-Entwurf mit Optionen, Empfehlung und Begründung vor.
- [x] Der Widerspruch Flutter gegen React (OD-01) ist mit beiden Quellen belegt dargestellt.
- [ ] Nach Freigabe durch den Benutzer sind die ADRs `accepted` und die OD-Einträge `decided`. Fünf von sechs sind erledigt, OD-02 fehlt noch.

Blockiert: OD-02 wird erst nach dem Spike F-04.11 entschieden. Das hat der Benutzer am 2026-11-23 so festgelegt.

### F-00.02 Repository-Grundgerüst

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.01 (OD-05)
- Quelle: ARCH §18.3
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: add Python repository skeleton` auf `develop`. Am 2026-11-23 gelaufen: `uv sync`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy`, `uv run pytest` (1 passed), alle ohne Befund.

Verzeichnisstruktur nach dem gewählten Layout anlegen, nur mit den Teilen, die M1 braucht. Python-Paket mit Paketverwaltung, Lockfile und Testgerüst.

- [x] Struktur entspricht dem ADR zu OD-05.
- [x] Ein leerer Test läuft lokal mit einem dokumentierten Befehl.
- [x] `.gitignore` deckt Build-Artefakte, Umgebungen und lokale Daten ab.

In M1 angelegt sind nur `src/mathlab/` und `tests/`. `lean/`, `web/`, `benchmarks/golden/` und `configs/` entstehen mit den Features, die sie brauchen (ADR-0005).

Referenzbeispiel aus ARCH §18.3, unverändert zitiert. Bei Abweichung gilt die Quelle. Der Baum ist das Zielbild. Maßgeblich ist das ADR zu OD-05, und in M1 entstehen nur die benötigten Teile.

```text
math-research-system/
├── apps/
│   ├── desktop/
│   ├── web/
│   └── cli/
├── services/
│   ├── api/
│   ├── orchestration/
│   ├── verification/
│   ├── experiment-tracking/
│   └── knowledge/
├── packages/
│   ├── core/
│   │   ├── problems/
│   │   ├── statements/
│   │   ├── proofs/
│   │   └── contracts/
│   ├── agents/
│   ├── strategies/
│   ├── search/
│   ├── metrics/
│   └── model-adapters/
├── engines/
│   ├── lean4/
│   ├── symbolic/
│   ├── numerical/
│   ├── smt/
│   └── simulation/
├── knowledge/
│   ├── graph/
│   ├── retrieval/
│   ├── embeddings/
│   └── memory/
├── ml/
│   ├── datasets/
│   ├── training/
│   ├── evaluation/
│   └── models/
├── benchmarks/
│   ├── golden/
│   ├── minif2f/
│   ├── proofnet/
│   └── custom/
├── experiments/
├── docs/
├── configs/
├── scripts/
└── .github/
```

### F-00.03 Toolchain-Pinning und Environment-Fingerprint

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02
- Quelle: ARCH §3.2, §9.2, §21 (Toolversionen); UI §19.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: add environment fingerprint` auf `develop`. Am 2026-11-23 gelaufen: `uv lock --check`, `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` (485 passed), alle ohne Befund. Fixierung über `.python-version` und `uv.lock` (beide eingecheckt, Test prüft das), ein Frontend gibt es noch nicht. Fingerprint in `src/mathlab/environment.py` (`uv run python -m mathlab.environment`), Tests in `tests/test_environment.py`, darunter Stabilität über Prozesse mit verschiedenem `PYTHONHASHSEED`. Lean, Mathlib und Solver sind noch nicht installiert und werden als `None` erfasst.

Alle Versionen werden fixiert, und eine Funktion erzeugt einen Fingerprint aus Python-, Lean-, Mathlib-, Solver- und Bibliotheksversionen sowie Git-Commit. Der Fingerprint wird später in jedem ProofAttempt gespeichert (F-09.02).

- [x] Lockfiles für Python und, falls vorhanden, Frontend sind eingecheckt.
- [x] Der Fingerprint ist deterministisch und ändert sich bei jeder Versionsänderung.
- [x] Ein Test belegt beide Eigenschaften.

### F-00.04 Container-Umgebung

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.03
- Quelle: ARCH §3.2 (Portabilität), §17.1 (Docker)
- Bearbeiter: offen · Nachweise: offen

Container für Backend, PostgreSQL und Engines (Lean, SymPy). Lokal unter Windows und Linux startbar.

- [ ] Ein Befehl startet Backend und Datenbank.
- [ ] Lean und Mathlib laufen im Container mit der gepinnten Version.
- [ ] Start unter Windows ist belegt.

### F-00.05 CI-Grundgates

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02
- Quelle: ARCH §21.1, §17.1 (GitHub Actions)
- Bearbeiter: offen · Nachweise: offen

CI prüft Formatierung, Linting, statische Typprüfung und Tests bei jedem Push.

- [ ] Workflow läuft und schlägt bei einem absichtlichen Formatfehler fehl.
- [ ] Typprüfung ist für das Core-Paket im strikten Modus aktiv.

### F-00.06 Fachliche CI-Gates

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-00.05, F-02.01, F-04.05, F-11.03
- Quelle: ARCH §21.1
- Bearbeiter: offen · Nachweise: offen

CI erweitert um reproduzierbare Lean-Testbeweise mit fixierter Mathlib, das Verbot von `sorry` und unerlaubten Axiomen in freigegebenen Beweisartefakten, Schema-Kompatibilität der Events und Engines, Golden-Smoke-Tests mit kleinem Budget, Simulationstests mit fixierten Seeds und sichtbare Regressionen bei Erfolgsquote und Kosten.

- [ ] Ein Beweisartefakt mit `sorry` lässt den CI-Lauf fehlschlagen.
- [ ] Eine inkompatible Schemaänderung lässt den CI-Lauf fehlschlagen.
- [ ] Golden-Smoke läuft unter einem festen Zeitlimit und berichtet Erfolgsquote und Kosten.

### F-00.07 Lizenzinventar

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: keine
- Quelle: ARCH §17.3 (Lizenzprüfung), §21 (Risiko Lizenzen)
- Bearbeiter: offen · Nachweise: offen

Inventar der Lizenzen aller eingesetzten Werkzeuge, Bibliotheken, Modellgewichte und Datensätze mit Vermerk zur Weitergabe.

- [ ] Datei `docs/licenses.md` listet jede Komponente mit Lizenz und Quelle.
- [ ] Neue Abhängigkeiten werden im Inventar ergänzt (Regel in AGENTS.md).

### F-00.08 Entwickler-Setup dokumentieren

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-00.04
- Quelle: ARCH §3.2
- Bearbeiter: offen · Nachweise: offen

Root-README mit Zweck, Setup unter Windows und Linux, Teststart und Verweis auf die Docs.

- [ ] Ein frisches Klonen und Befolgen der README führt zu grünen Tests.

### F-00.09 Sicherung des Datenordners

- Status: `ready` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-02.07
- Quelle: ADR-0006
- Bearbeiter: offen · Nachweise: offen

Der Datenordner `D:\MathLabData` (überschreibbar über `MATHLAB_DATA_DIR`) wird nach `D:\Sicherungen\MathLab` gesichert. Die Sicherung ist konsistent mit dem Event Store und verändert keine bestehenden Artefakte.

- [ ] Ein dokumentierter Befehl erzeugt eine zeitgestempelte Sicherung unter `D:\Sicherungen\MathLab`.
- [ ] Eine Wiederherstellung in ein leeres Verzeichnis ist getestet, und die Content-Hashes der Artefakte stimmen überein.
