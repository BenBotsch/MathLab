# E14 Backend API, Live Stream und Control API

- Status: `todo` · Meilenstein: M1, Ausbau M2, M3 und M6
- Quellen: ARCH §3.2, §18.2, §18.3, §19 (Phase 1); UI §5.3, §10.2, §15.1, §15.2, §16.3, §16.4, §17.2, §18.2, §19, §21 (Epics UI-01 und UI-07)
- Abhängige Epics: E01, E02, E07

## Ziel

Python und FastAPI stellen einen versionierten Lesezugriff, einen SSE-Eventstrom und eine getrennte Control API für Kommandos bereit. Die Oberfläche und die CLI greifen ausschließlich über diese Schnittstellen auf das System zu.

## Abgrenzung

Eventschema, Event Store, Snapshots und Idempotenz der Speicherung liegen in E02. Die Bedienelemente für Kommandos liegen in E20. Rechte und Rollen liegen in F-24.03.

## Invarianten

Der Server ist für mathematische und operative Fakten maßgeblich (UI §15.3). Die UI mutiert die Datenbank nie direkt (UI §18.3). Große Beweisterme und Logs gehen nicht durch den Live-Stream, sondern als Artefakt-ID (UI §16.4). Kein Kommando kann einen Knoten auf `VERIFIED` setzen.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-14.01 | FastAPI-Grundgerüst und versioniertes API-Schema | `todo` | P0 | M1 |
| F-14.02 | Lese-Endpunkte | `todo` | P0 | M1 |
| F-14.03 | SSE-Live-Stream und Event-Nachladung | `todo` | P0 | M1 |
| F-14.04 | Command API mit Serverbestätigung | `todo` | P0 | M1 |
| F-14.05 | Erkennung konkurrierender Kommandos | `todo` | P0 | M1 |
| F-14.06 | Artefaktverweise statt großer Payloads | `todo` | P0 | M1 |
| F-14.07 | Verhalten bei Verbindungs- und Komponentenausfällen | `todo` | P0 | M1 |
| F-14.08 | Endpunkt für Wissenssuche | `todo` | P1 | M3 |
| F-14.09 | CLI-App | `todo` | P0 | M1 |
| F-14.10 | WebSockets bei nachgewiesenem Bedarf | `todo` | P2 | M6 |
| F-14.11 | Interner Research Event Bus | `todo` | P0 | M1 |

## Features

### F-14.01 FastAPI-Grundgerüst und versioniertes API-Schema

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02, F-01.02
- Quelle: UI §16.4 (letzter Absatz), §19 (Backend); ARCH §18.2 (Versionierung, Fehlertypen, Trace-IDs)
- Bearbeiter: offen · Nachweise: offen

FastAPI-Anwendung mit OpenAPI-Schema, Versionspräfix, einheitlichen Fehlertypen und Trace-ID in jeder Antwort.

- [ ] Das OpenAPI-Schema ist versioniert und wird in CI auf Kompatibilität geprüft (F-00.06).
- [ ] Jede Fehlerantwort enthält Fehlertyp und Trace-ID.

### F-14.02 Lese-Endpunkte

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01, F-02.05, F-02.06, F-02.07
- Quelle: UI §16.4
- Bearbeiter: offen · Nachweise: offen

`GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/snapshot`, `GET /runs/{id}/proof-graph`, `GET /runs/{id}/agent-graph`, `GET /proof-nodes/{id}` und `GET /artifacts/{id}`. Die Pfade in UI §16.4 sind illustrativ und werden im API-Schema festgelegt.

- [ ] Jeder Endpunkt hat einen Contract-Test.
- [ ] Ein Snapshot ist konsistent zu einer genannten Eventsequenz.

### F-14.03 SSE-Live-Stream und Event-Nachladung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01, F-02.03
- Quelle: UI §15.2, §16.4 (`/stream`, `/events?after=`), §17.2, §21 (Epic UI-01)
- Bearbeiter: offen · Nachweise: offen

SSE-Endpunkt pro Run mit der Sequenznummer als Event-ID und ein Endpunkt zum Nachladen ab einer Sequenz.

- [ ] Ein Client, der mit `Last-Event-ID` neu verbindet, erhält alle verpassten Events in Reihenfolge.
- [ ] Ein Agentenevent erscheint während der Ausführung im Stream (UI §20, Kriterium 1).

### F-14.04 Command API mit Serverbestätigung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01, F-02.04, F-07.03
- Quelle: UI §10.2, §16.3, §5.3, §21 (Epic UI-07)
- Bearbeiter: offen · Nachweise: offen

`POST /runs/{id}/commands` mit `command_id`, `type`, `run_id`, optional `branch_id`, `agent_id` und `proof_node_id`, dazu `requested_by`, `expected_state_version` und `parameters`. Antwort ist eine Bestätigung mit neuem Zustandsstand oder ein begründeter Fehler. Jedes Kommando erzeugt ein Audit-Event. Die Control API ist vom Lesezugriff getrennt.

- [ ] Ein wiederholt gesendetes Kommando mit gleicher `command_id` wird genau einmal ausgeführt.
- [ ] Jedes angenommene oder abgelehnte Kommando ist als Audit-Event im Log.
- [ ] Ein Kommando, das `VERIFIED` setzen soll, existiert nicht und wird abgelehnt (Test).

### F-14.05 Erkennung konkurrierender Kommandos

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.04
- Quelle: UI §10.2 (`expected_state_version`), §18.2 (Commands gleichzeitig)
- Bearbeiter: offen · Nachweise: offen

Stimmt `expected_state_version` nicht mit dem aktuellen Stand überein, wird das Kommando mit Versionskonflikt abgelehnt und der Client lädt den neuesten Zustand.

- [ ] Zwei gleichzeitige Kommandos auf denselben Stand ergeben genau eine Ausführung und einen Konflikt.

### F-14.06 Artefaktverweise statt großer Payloads

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.03, F-02.07
- Quelle: UI §16.4 (letzter Absatz), §17.2, §18.2 (große Events)
- Bearbeiter: offen · Nachweise: offen

Payloads oberhalb einer konfigurierten Größe werden im Artefaktspeicher abgelegt. Der Stream überträgt nur die Artefakt-ID.

- [ ] Ein Event mit großem Lean-Log enthält im Stream nur die ID, das Artefakt ist über F-14.02 abrufbar.

### F-14.07 Verhalten bei Verbindungs- und Komponentenausfällen

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.03, F-02.08
- Quelle: UI §18.2
- Bearbeiter: offen · Nachweise: offen

Das Backend liefert für die Fehlerfälle aus UI §18.2 die nötigen Zustände. Ein abgestürzter Agent erhält einen Fehlerstatus mit letzter bekannter Aktivität. Ist der Verifier nicht verfügbar, bleibt der Prüfstatus offen oder unterbrochen. Nach einem Backend-Neustart wird der Snapshot geladen und die Eventsequenz fortgesetzt. Die Fälle Versionskonflikt, große Events und Replay liegen in F-14.05, F-14.06 und F-19.07.

- [ ] Für jeden der vier hier behandelten Fehlerfälle gibt es einen Integrationstest.
- [ ] Ein Verifier-Ausfall führt nie zu einem gültigen Prüfstatus.

### F-14.08 Endpunkt für Wissenssuche

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-14.01, F-10.06
- Quelle: UI §16.4 (`/knowledge/search`)
- Bearbeiter: offen · Nachweise: offen

Theorem- und Lemma-Suche über die Retrieval-Pipeline. Jeder Treffer enthält seine Vertrauensebene.

- [ ] Nicht verifizierte Treffer sind in der Antwort als solche markiert.

### F-14.09 CLI-App

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.04, F-14.03
- Quelle: ARCH §18.3 (`apps/cli`), §19 (Phase 1, CLI oder einfache Web-UI)
- Bearbeiter: offen · Nachweise: offen

Kommandozeile zum Starten, Beobachten, Pausieren und Beenden von Runs sowie zum Starten der Golden Suite. Nutzt dieselbe API wie die Oberfläche.

- [ ] Die Odd-Sum-Aufgabe lässt sich vollständig über die CLI lösen und das Ergebnis abrufen.

### F-14.10 WebSockets bei nachgewiesenem Bedarf

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-14.03
- Quelle: UI §15.2
- Bearbeiter: offen · Nachweise: offen

WebSockets werden erst eingeführt, wenn eine konkrete Interaktion wie Kollaboration sie benötigt.

- [ ] Der Bedarf ist in einem ADR begründet, bevor implementiert wird.

### F-14.11 Interner Research Event Bus

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.03, F-00.01 (OD-04)
- Quelle: UI §15.1, §15.2 (interne Backend-Kommunikation)
- Bearbeiter: offen · Nachweise: offen

Agenten, CAS und Solver veröffentlichen Ergebnisse über einen Bus oder eine Queue. Der Bus schreibt in den Event Store und speist den Live-Stream, der Orchestrator abonniert ihn. Die Wahl der Technik folgt OD-04.

- [ ] Ein Event wird genau einmal persistiert, auch wenn der Bus es mehrfach zustellt.
