# Backlog

Zentrale Statusübersicht aller Epics und Features. Die maßgeblichen Angaben stehen in den Epic-Dateien unter [epics/](epics/). Diese Übersicht wird bei jedem Statuswechsel nachgezogen. Den Ablauf beschreibt [WORKFLOW.md](WORKFLOW.md), die Meilensteine beschreibt [ROADMAP.md](ROADMAP.md).

## Stand

260 Features in 26 Epics. Erledigt sind 12 von 260.

| Status | Anzahl |
| --- | --- |
| `todo` | 233 |
| `ready` | 14 |
| `in-progress` | 0 |
| `review` | 0 |
| `done` | 12 |
| `blocked` | 1 |
| `dropped` | 0 |

## Epics

Fortschritt zählt Features mit Status `done` gegen alle nicht verworfenen Features des Epics.

| Epic | Titel | Meilenstein | P0 | P1 | P2 | Status | Fortschritt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E00 | [Projektfundament](epics/E00-projektfundament.md) | M1, Ausbau M2 | 5 | 4 | 0 | `in-progress` | 2/9 |
| E01 | [Core-Domänenmodell und Contracts](epics/E01-core-domaenenmodell.md) | M1 | 7 | 0 | 0 | `done` | 7/7 |
| E02 | [Event Sourcing und Persistenz](epics/E02-event-sourcing-persistenz.md) | M1 | 8 | 1 | 0 | `in-progress` | 3/9 |
| E03 | [Problem Engine](epics/E03-problem-engine.md) | M1, Ausbau M2 und M5 | 3 | 5 | 1 | `todo` | 0/9 |
| E04 | [Formal Verification Engine](epics/E04-formal-verification.md) | M1, Ausbau M2 | 8 | 3 | 0 | `todo` | 0/11 |
| E05 | [Symbolik, SMT, Numerik und Widerlegung](epics/E05-symbolik-smt-numerik.md) | M1, Ausbau M2, M5 und M6 | 3 | 4 | 2 | `todo` | 0/9 |
| E06 | [Strategy Engine und Beweismethodenkatalog](epics/E06-strategy-engine.md) | M2, Ausbau M3 und M4 | 3 | 3 | 0 | `todo` | 0/6 |
| E07 | [Agent Orchestrator und Multiagentensystem](epics/E07-agent-orchestrator.md) | M1, Ausbau M2 bis M6 | 6 | 8 | 2 | `todo` | 0/16 |
| E08 | [Proof Search Engine](epics/E08-proof-search.md) | M1, Ausbau M2, M4 und M6 | 5 | 5 | 1 | `todo` | 0/11 |
| E09 | [Trial-and-Error und Experiment Tracking](epics/E09-trial-and-error-tracking.md) | M1, Ausbau M2 und M4 | 4 | 3 | 0 | `todo` | 0/7 |
| E10 | [Wissensgraph und mathematisches Langzeitgedächtnis](epics/E10-wissensgraph.md) | M3, Vorstufe M2, Ausbau M6 | 7 | 4 | 1 | `todo` | 0/12 |
| E11 | [Benchmarks, Betriebsmodi und Evaluation](epics/E11-benchmarks-evaluation.md) | M1, Ausbau M2 bis M6 | 7 | 6 | 1 | `todo` | 0/14 |
| E12 | [Metriken, Reward und Lernverfahren](epics/E12-metriken-lernen.md) | M4, Vorstufen M1 und M2, Ausbau M6 | 2 | 10 | 1 | `todo` | 0/13 |
| E13 | [Explanation Engine und Research Reports](epics/E13-explanation-reports.md) | M5, Vorstufe M2 | 1 | 6 | 4 | `todo` | 0/11 |
| E14 | [Backend API, Live Stream und Control API](epics/E14-backend-api.md) | M1, Ausbau M2, M3 und M6 | 9 | 1 | 1 | `todo` | 0/11 |
| E15 | [Research Shell und Designsystem](epics/E15-research-shell.md) | M1, Ausbau M2 und M5 | 8 | 4 | 2 | `todo` | 0/14 |
| E16 | [Proof Search Graph UI](epics/E16-proof-graph-ui.md) | M1, Ausbau M2 | 5 | 4 | 0 | `todo` | 0/9 |
| E17 | [Inspector](epics/E17-inspector.md) | M1, Ausbau M2 und M5 | 5 | 5 | 0 | `todo` | 0/10 |
| E18 | [Agent Explorer und Agent Execution Graph](epics/E18-agent-explorer.md) | M1, Ausbau M2 | 2 | 5 | 1 | `todo` | 0/8 |
| E19 | [Timeline, Console und Replay](epics/E19-timeline-replay.md) | M1, Ausbau M2 | 5 | 5 | 0 | `todo` | 0/10 |
| E20 | [Human-in-the-Loop](epics/E20-human-in-the-loop.md) | M1, Ausbau M2 | 3 | 8 | 0 | `todo` | 0/11 |
| E21 | [Knowledge and Experiment Laboratory UI](epics/E21-labs-ui.md) | M2, Ausbau M3 bis M5 | 1 | 10 | 0 | `todo` | 0/11 |
| E22 | [Workflow Builder und visuelle Orchestrierung](epics/E22-workflow-builder.md) | M6 | 0 | 5 | 3 | `todo` | 0/8 |
| E23 | [Observability und Tracing](epics/E23-observability.md) | M1, Ausbau M2 | 2 | 2 | 1 | `todo` | 0/5 |
| E24 | [Sicherheit, Sandbox und Risikoregister](epics/E24-sicherheit-sandbox.md) | M1, Ausbau M2 und M3 | 7 | 2 | 0 | `todo` | 0/9 |
| E25 | [Eigenständige Forschung und Forschungsbeiträge](epics/E25-forschungsbeitraege.md) | M6 | 0 | 6 | 4 | `todo` | 0/10 |

## Now

Blockiert: [F-00.01](epics/E00-projektfundament.md#f-0001-architekturentscheidungen-für-m1-vorbereiten) Architekturentscheidungen für M1 vorbereiten (P0, M1). Fünf von sechs ADRs sind angenommen, OD-02 wartet auf den Spike F-04.11.

Features mit Status `ready`. Sie haben keine offenen Abhängigkeiten und dürfen gezogen werden.

| Feature | Titel | Priorität | Meilenstein |
| --- | --- | --- | --- |
| [F-00.04](epics/E00-projektfundament.md#f-0004-container-umgebung) | Container-Umgebung | P0 | M1 |
| [F-00.05](epics/E00-projektfundament.md#f-0005-ci-grundgates) | CI-Grundgates | P0 | M1 |
| [F-07.02](epics/E07-agent-orchestrator.md#f-0702-typisierte-agentennachrichten) | Typisierte Agentennachrichten | P0 | M1 |
| [F-00.09](epics/E00-projektfundament.md#f-0009-sicherung-des-datenordners) | Sicherung des Datenordners | P1 | M1 |
| [F-03.01](epics/E03-problem-engine.md#f-0301-import-von-text-latex-und-lean) | Import von Text, LaTeX und Lean | P0 | M1 |
| [F-05.07](epics/E05-symbolik-smt-numerik.md#f-0507-gegenbeispiel-objekt) | Gegenbeispiel-Objekt | P0 | M1 |
| [F-14.01](epics/E14-backend-api.md#f-1401-fastapi-grundgerüst-und-versioniertes-api-schema) | FastAPI-Grundgerüst und versioniertes API-Schema | P0 | M1 |
| [F-15.01](epics/E15-research-shell.md#f-1501-client-grundgerüst) | Client-Grundgerüst | P0 | M1 |
| [F-11.01](epics/E11-benchmarks-evaluation.md#f-1101-golden-problemliste-für-m1-ausarbeiten) | Golden-Problemliste für M1 ausarbeiten | P0 | M1 |
| [F-24.02](epics/E24-sicherheit-sandbox.md#f-2402-toolrechte-pro-agentenrolle) | Toolrechte pro Agentenrolle | P0 | M1 |
| [F-24.04](epics/E24-sicherheit-sandbox.md#f-2404-secrets-und-privacy_classification) | Secrets und `privacy_classification` | P0 | M1 |
| [F-24.09](epics/E24-sicherheit-sandbox.md#f-2409-risikoregister) | Risikoregister | P0 | M1 |
| [F-02.09](epics/E02-event-sourcing-persistenz.md#f-0209-schema-versionierung-und-migration) | Schema-Versionierung und Migration | P1 | M2 |
| [F-05.04](epics/E05-symbolik-smt-numerik.md#f-0504-simulationsworkflow-mit-seed-und-präzision) | Simulationsworkflow mit Seed und Präzision | P1 | M2 |

## Next

M1-Features, die als Nächstes `ready` werden können. Es sind die Stufen 1 bis 3 der [Reihenfolge in M1](ROADMAP.md#reihenfolge-in-m1). Ein Feature wird `ready`, wenn seine Abhängigkeiten `done` sind und jede genannte offene Entscheidung (OD) als ADR entschieden ist.

| Feature | Titel | Priorität | Abhängigkeiten |
| --- | --- | --- | --- |
| [F-00.04](epics/E00-projektfundament.md#f-0004-container-umgebung) | Container-Umgebung | P0 | F-00.03 |
| [F-04.11](epics/E04-formal-verification.md#f-0411-spike-lean-interaktionsschicht) | Spike Lean-Interaktionsschicht | P0 | F-00.03, F-11.01 |
| [F-15.02](epics/E15-research-shell.md#f-1502-globale-navigation) | Globale Navigation | P0 | F-15.01 |
| [F-15.03](epics/E15-research-shell.md#f-1503-workspace-layout-und-panelverwaltung) | Workspace-Layout und Panelverwaltung | P0 | F-15.01 |
| [F-15.06](epics/E15-research-shell.md#f-1506-design-tokens-hell--und-dunkelmodus) | Design Tokens, Hell- und Dunkelmodus | P0 | F-15.01 |

## Later

Alle übrigen Features nach Meilenstein. Die Reihenfolge innerhalb von M1 steht in [ROADMAP.md](ROADMAP.md#reihenfolge-in-m1).

| Meilenstein | Übrige offen | davon P0 | davon P1 | davon P2 |
| --- | --- | --- | --- | --- |
| [M1](ROADMAP.md#m1) | 93 | 75 | 18 | 0 |
| [M2](ROADMAP.md#m2) | 74 | 11 | 61 | 2 |
| [M3](ROADMAP.md#m3) | 14 | 4 | 10 | 0 |
| [M4](ROADMAP.md#m4) | 13 | 1 | 12 | 0 |
| [M5](ROADMAP.md#m5) | 17 | 1 | 7 | 9 |
| [M6](ROADMAP.md#m6) | 25 | 0 | 11 | 14 |
