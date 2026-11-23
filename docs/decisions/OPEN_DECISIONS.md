# Offene Entscheidungen

Die Konzeptdokumente lassen diese Punkte offen oder widersprechen sich. Jeder Eintrag blockiert die genannten Features, bis ein ADR vorliegt. Die Vorbereitung aller M1-relevanten Einträge ist Feature [F-00.01](../backlog/epics/E00-projektfundament.md).

| ID | Frage | Status | Blockiert |
| --- | --- | --- | --- |
| OD-01 | Client-Plattform der Oberfläche | `decided` ([ADR-0001](adr-0001-client-plattform.md)) | F-15.01 |
| OD-02 | Lean-Interaktionsschicht | `open` | F-04.02 (wartet auf Spike F-04.11) |
| OD-03 | Modellprovider und lokale Modelle | `decided` ([ADR-0003](adr-0003-modellprovider.md)) | F-07.01, F-07.04 |
| OD-04 | Workflow- und Task-Ausführung | `decided` ([ADR-0004](adr-0004-workflow-ausfuehrung.md)) | F-07.03 |
| OD-05 | Repository-Layout und Build-Werkzeuge | `decided` ([ADR-0005](adr-0005-repository-layout.md)) | F-00.02 |
| OD-06 | Artefaktspeicher | `decided` ([ADR-0006](adr-0006-artefaktspeicher.md)) | F-02.07 |
| OD-07 | Golden-Problemliste für M1 | `open` | F-11.03, F-11.04 |

## OD-01 Client-Plattform der Oberfläche

Entschieden: [ADR-0001](adr-0001-client-plattform.md) (`accepted`, 2026-11-23).

Die Quellen widersprechen sich. ARCH §17.1 empfiehlt Flutter als Desktop-Client und React nur optional für ein Web-Dashboard. UI §19 und §19.1 empfehlen zuerst ein lokales React-/TypeScript-Frontend, weil React Flow, Cytoscape.js und Plotly direkt nutzbar sind, und Flutter höchstens später als äußere Shell mit eingebetteten Webflächen.

Optionen sind React und TypeScript im Browser gegen ein lokales FastAPI-Backend, dasselbe Frontend in einem Desktop-Wrapper, oder Flutter-Desktop mit eingebetteten Web-Views für die Graphen. Das UI-Konzept ist das jüngere und spezifischere Dokument und spricht für React zuerst. Entscheiden muss der Benutzer, weil bestehende Flutter-Projekte eine Rolle spielen (UI §19.1).

## OD-02 Lean-Interaktionsschicht

Entwurf: [ADR-0002](adr-0002-lean-interaktion.md) (`proposed`). Vor der Entscheidung läuft der Spike F-04.11.

ARCH §17.1 nennt LeanDojo und Pantograph. Zu klären sind Unterstützung der gepinnten Lean- und Mathlib-Version, Zugriff auf Proof States und Taktikausführung, Lauffähigkeit unter Windows oder nur im Linux-Container, Lizenz und Wartungsstand. Vor der Entscheidung ist ein kurzer Spike mit beiden Werkzeugen sinnvoll.

## OD-03 Modellprovider und lokale Modelle

Entschieden: [ADR-0003](adr-0003-modellprovider.md) (`accepted`, 2026-11-23).

ARCH §17.3 geht von einer NVIDIA Quadro RTX 4000 mit 8 GB VRAM aus und empfiehlt kleine lokale Proof-Modelle plus austauschbare externe Provider. Zu entscheiden sind der erste Provider für den Proof-Agenten in M1, ob und welches lokale Modell parallel evaluiert wird (F-12.10) und welches Kostenbudget pro Benchmarklauf gilt. Die Adapter-Schicht (F-07.01) bleibt in jedem Fall providerneutral.

## OD-04 Workflow- und Task-Ausführung

Entschieden: [ADR-0004](adr-0004-workflow-ausfuehrung.md) (`accepted`, 2026-11-23).

ARCH §17.1 empfiehlt eine eigene typisierte Python-Engine und später eine Task Queue. Zu entscheiden ist, ob M1 synchron im Prozess läuft, mit `asyncio` oder schon mit einer Queue, und wie Pause, Resume und Checkpoints (F-08.05) technisch umgesetzt werden.

## OD-05 Repository-Layout und Build-Werkzeuge

Entschieden: [ADR-0005](adr-0005-repository-layout.md) (`accepted`, 2026-11-23).

ARCH §18.3 skizziert ein Monorepo mit `apps/`, `services/`, `packages/`, `engines/`, `knowledge/`, `ml/` und `benchmarks/`. ARCH §18.3 empfiehlt außerdem, zu Beginn nur eine modularisierte gemeinsame Codebasis zu führen. Zu entscheiden sind Python-Paketverwaltung und Lockfile, Minimum-Python-Version, Frontend-Paketverwaltung (nach OD-01) und welche Verzeichnisse in M1 tatsächlich angelegt werden.

## OD-06 Artefaktspeicher

Entschieden: [ADR-0006](adr-0006-artefaktspeicher.md) (`accepted`, 2026-11-23).

ARCH §17.1 und §17.2 sehen zuerst das Dateisystem und später S3-kompatiblen Speicher vor. Zu entscheiden sind Ablageort, Namensschema über Content-Hash, Aufbewahrung und ob Artefakte im Container-Volume oder auf dem Host liegen.

## OD-07 Golden-Problemliste für M1

ARCH §19 Phase 1 verlangt 20 bis 50 Aufgaben aus einer fixierten Benchmarkliste. Zu entscheiden sind Zusammensetzung (eigene Golden Tasks der Level 1 bis 3 aus ARCH §16.2, Auswahl aus miniF2F), die formalen Lean-Aussagen und welche Aufgaben als Blind-Rediscovery-Holdout dienen. Die Ausarbeitung ist Feature F-11.01.
