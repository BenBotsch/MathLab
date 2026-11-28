# E23 Observability und Tracing

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §3.2 (Nachvollziehbarkeit), §17.1, §18.2 (Trace-IDs); UI §12.1, §16.2, §17.1, §19
- Abhängige Epics: E02, E07, E14

## Ziel

Technische Ausführung und mathematischer Verlauf sind getrennt erfasst und über IDs verknüpft. Kosten, Ressourcen, Fehler und Latenzen jedes Agenten- und Toolaufrufs sind messbar.

## Abgrenzung

Das mathematische Tracing ist das eigene Domänenmodell aus E01, E02 und E09. OpenTelemetry und Langfuse ergänzen es und ersetzen es nicht (UI §17.1).

## Invarianten

Keine Secrets in Logs, Spans oder Traces (UI §18.3). Jedes Event und jeder Span trägt eine Trace-ID.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-23.01 | Trace-ID-Propagation | `ready` | P0 | M1 |
| F-23.02 | OpenTelemetry-Spans | `todo` | P1 | M2 |
| F-23.03 | Langfuse-Anbindung | `todo` | P2 | M2 |
| F-23.04 | Verknüpfung technischer und mathematischer Traces | `todo` | P1 | M2 |
| F-23.05 | Strukturiertes Logging, Ressourcen- und Kostenerfassung | `todo` | P0 | M1 |

## Features

### F-23.01 Trace-ID-Propagation

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.01, F-14.01
- Quelle: UI §16.2 (Pflichtfelder), ARCH §18.2
- Bearbeiter: offen · Nachweise: offen

Eine Trace-ID entsteht beim Kommando oder Run-Start und wird über API, Bus, Orchestrator, Agenten, Tools und Events weitergereicht.

- [ ] Für einen Odd-Sum-Run lassen sich alle Events und Logs über eine Trace-ID finden.

### F-23.02 OpenTelemetry-Spans

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-23.01
- Quelle: UI §17.1, §19; ARCH §17.1
- Bearbeiter: offen · Nachweise: offen

Spans für Agenten-Calls, Toolaufträge, Queuezeiten, API-Aufrufe, Retries und Fehler mit OTel-Export.

- [ ] Ein Lean-Aufruf erscheint als Span mit Dauer, Ergebnis und `proof_node_id`.

### F-23.03 Langfuse-Anbindung

- Status: `todo` · Priorität: P2 · Meilenstein: M2
- Abhängigkeiten: F-23.02, F-07.01
- Quelle: UI §17.1, §19; ARCH §17.1
- Bearbeiter: offen · Nachweise: offen

Optionale Anbindung für Agenten-, Session-, Graph- und Timeline-Ansichten von LLM-Aufrufen. Prompts werden vor dem Export auf Secrets und `privacy_classification` geprüft.

- [ ] Ohne Konfiguration läuft das System ohne Langfuse.

### F-23.04 Verknüpfung technischer und mathematischer Traces

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-23.02, F-09.01
- Quelle: UI §17.1, §21 (Epic UI-05)
- Bearbeiter: offen · Nachweise: offen

Spans tragen `run_id`, `branch_id`, `proof_node_id` und `attempt_id`. Mathematische Events tragen die Trace-ID. Beide Richtungen sind abfragbar.

- [ ] Zu jedem ProofAttempt sind die zugehörigen Spans abrufbar.

### F-23.05 Strukturiertes Logging, Ressourcen- und Kostenerfassung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-23.01, F-07.01
- Quelle: UI §12.1 (CPU, GPU, Speicher, Token); ARCH §9.2, §17.3
- Bearbeiter: offen · Nachweise: offen

JSON-Logs mit Trace-ID sowie Erfassung von CPU, GPU, Speicher, Token und Modellkosten pro Aufruf, aggregiert pro Agent und Run.

- [ ] Run-Kennzahlen aus F-09.05 beziehen Ressourcen und Kosten aus dieser Erfassung.
- [ ] Ein Test prüft, dass ein bekanntes Test-Secret nicht in Logs erscheint.
