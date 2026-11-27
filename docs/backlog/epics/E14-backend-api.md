# E14 Backend API, Live Stream und Control API

- Status: `in-progress` · Meilenstein: M1, Ausbau M2, M3 und M6
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
| F-14.01 | FastAPI-Grundgerüst und versioniertes API-Schema | `done` | P0 | M1 |
| F-14.02 | Lese-Endpunkte | `review` | P0 | M1 |
| F-14.03 | SSE-Live-Stream und Event-Nachladung | `done` | P0 | M1 |
| F-14.04 | Command API mit Serverbestätigung | `ready` | P0 | M1 |
| F-14.05 | Erkennung konkurrierender Kommandos | `todo` | P0 | M1 |
| F-14.06 | Artefaktverweise statt großer Payloads | `ready` | P0 | M1 |
| F-14.07 | Verhalten bei Verbindungs- und Komponentenausfällen | `ready` | P0 | M1 |
| F-14.08 | Endpunkt für Wissenssuche | `todo` | P1 | M3 |
| F-14.09 | CLI-App | `todo` | P0 | M1 |
| F-14.10 | WebSockets bei nachgewiesenem Bedarf | `ready` | P2 | M6 |
| F-14.11 | Interner Research Event Bus | `review` | P0 | M1 |

## Features

### F-14.01 FastAPI-Grundgerüst und versioniertes API-Schema

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02, F-01.02
- Quelle: UI §16.4 (letzter Absatz), §19 (Backend); ARCH §18.2 (Versionierung, Fehlertypen, Trace-IDs)
- Bearbeiter: Claude · Nachweise: `src/mathlab/api/` mit `create_app()`, Präfix `/api/v1`, `GET /api/v1/health`, Header `X-Trace-Id` (gültige Client-UUID wird übernommen, sonst neu erzeugt) und `ErrorResponse` mit `ErrorType` und `trace_id` für Validierungs-, HTTP-, Engine- und unerwartete Fehler. Interne Fehlertexte werden nicht ausgegeben. `docs/reference/openapi-v1.json` wird mit `python -m mathlab.api.openapi` erzeugt; `--check` meldet Abweichungen, `--against` meldet Brüche (entfernte Pfade oder Operationen, neue Pflichtparameter). CI-Schritt „OpenAPI schema“ in `.github/workflows/ci.yml`. `tests/test_api.py` mit 14 Tests. ruff, ruff format und mypy strict ohne Befund; pytest 908 passed, 55 skipped. Der Vergleich gegen den Stand auf `main` bleibt Teil von F-00.06.

FastAPI-Anwendung mit OpenAPI-Schema, Versionspräfix, einheitlichen Fehlertypen und Trace-ID in jeder Antwort.

- [x] Das OpenAPI-Schema ist versioniert und wird in CI auf Kompatibilität geprüft (F-00.06).
- [x] Jede Fehlerantwort enthält Fehlertyp und Trace-ID.

### F-14.02 Lese-Endpunkte

- Status: `review` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01, F-02.05, F-02.06, F-02.07
- Quelle: UI §16.4
- Bearbeiter: Claude · Nachweise: Endpunkte in `src/mathlab/api/read.py`, Tests in `tests/test_api_read.py`, `PostgresEventStore.run_ids` mit Test in `tests/storage/test_events.py`, OpenAPI-Dokument `docs/reference/openapi-v1.json` neu erzeugt. Am 2026-11-27 liefen `ruff format --check`, `ruff check`, `mypy` (strict), `python -m mathlab.api.openapi --check` und `--against` gegen das vorherige v1-Dokument (keine brechende Änderung) sowie `pytest` mit 931 passed und 57 skipped, alle ohne Befund. Beleg Snapshot: Für jede Sequenz 1 bis 8 und für eine Sequenz über dem Ende gleicht `GET /runs/{run_id}/snapshot?at=n` dem `rebuild` der ersten n Ereignisse und nennt `sequence`, `snapshot_version` und `snapshot_sequence`. Festlegungen im Schema: Proof-Nodes liegen unter `/runs/{run_id}/proof-nodes/{node_id}`, weil der Store keinen Index von Knoten auf Runs hat. Artefakte werden als `application/octet-stream` ausgeliefert, solange der Medientyp nicht gespeichert wird. Der Agent-Graph enthält vorerst nur Agentenzustände, Kanten folgen mit E18. Ohne konfiguriertes Backend antworten die Endpunkte mit `UNAVAILABLE`. Offen vor `done`: Der Postgres-Test `test_run_ids_lists_every_run_with_events` wurde übersprungen, weil `MATHLAB_TEST_DATABASE_URL` nicht gesetzt war.

`GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/snapshot`, `GET /runs/{id}/proof-graph`, `GET /runs/{id}/agent-graph`, `GET /proof-nodes/{id}` und `GET /artifacts/{id}`. Die Pfade in UI §16.4 sind illustrativ und werden im API-Schema festgelegt.

- [x] Jeder Endpunkt hat einen Contract-Test.
- [x] Ein Snapshot ist konsistent zu einer genannten Eventsequenz.

### F-14.03 SSE-Live-Stream und Event-Nachladung

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01, F-02.03
- Quelle: UI §15.2, §16.4 (`/stream`, `/events?after=`), §17.2, §21 (Epic UI-01)
- Bearbeiter: Claude · Nachweise: Endpunkte in `src/mathlab/api/stream.py`, Tests in `tests/test_api_stream.py`. Der Bus beendet nach `close` auch spätere Abonnements sofort, der Test dafür steht in `tests/test_bus.py`. Das OpenAPI-Dokument `docs/reference/openapi-v1.json` ist neu erzeugt. Am 2026-11-27 liefen `ruff format --check`, `ruff check`, `mypy` (strict), `python -m mathlab.api.openapi --check` und `--against` gegen das vorherige v1-Dokument (keine brechende Änderung) sowie `pytest` mit 938 passed und 57 skipped, alle ohne Befund. Die Stream-Tests liefen dreimal hintereinander grün. Belege: Ein Client trennt nach Event 2, während der Trennung entstehen 4 und 5. Bei erneuter Verbindung mit `Last-Event-ID: 2` erhält er über HTTP 3, 4 und 5 in Reihenfolge. Ein `agent.started` erscheint im Stream, bevor der Run endet. Ein Event, das während des Nachladens aus dem Store veröffentlicht wird, kommt genau einmal an. Festlegungen: SSE-`id` ist die Sequenz, `event` der Eventtyp, `data` der Envelope als JSON. Der Startpunkt ist `Last-Event-ID`, sonst `?after=`, sonst 0. Ein leerlaufender Stream sendet alle 15 s einen Kommentar als Keep-alive. Fällt ein Abonnent hinter den Bus zurück, endet der Stream und der Client verbindet mit `Last-Event-ID` neu. `GET /runs/{run_id}/events` liefert höchstens 1000 Events pro Abruf.

SSE-Endpunkt pro Run mit der Sequenznummer als Event-ID und ein Endpunkt zum Nachladen ab einer Sequenz.

- [x] Ein Client, der mit `Last-Event-ID` neu verbindet, erhält alle verpassten Events in Reihenfolge.
- [x] Ein Agentenevent erscheint während der Ausführung im Stream (UI §20, Kriterium 1).

### F-14.04 Command API mit Serverbestätigung

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01, F-02.04, F-07.03
- Quelle: UI §10.2, §16.3, §5.3, §21 (Epic UI-07)
- Bearbeiter: offen · Nachweise: offen

`POST /runs/{id}/commands` mit `command_id`, `type`, `run_id`, optional `branch_id`, `agent_id` und `proof_node_id`, dazu `requested_by`, `expected_state_version` und `parameters`. Antwort ist eine Bestätigung mit neuem Zustandsstand oder ein begründeter Fehler. Jedes Kommando erzeugt ein Audit-Event. Die Control API ist vom Lesezugriff getrennt.

- [ ] Ein wiederholt gesendetes Kommando mit gleicher `command_id` wird genau einmal ausgeführt.
- [ ] Jedes angenommene oder abgelehnte Kommando ist als Audit-Event im Log.
- [ ] Ein Kommando, das `VERIFIED` setzen soll, existiert nicht und wird abgelehnt (Test).

Referenzbeispiel aus UI §16.3, unverändert zitiert. Bei Abweichung gilt die Quelle.

```json
{
  "command_id": "cmd-00119",
  "type": "branch.investigate",
  "run_id": "run-0042",
  "branch_id": "branch-induction-03",
  "requested_by": "user",
  "expected_state_version": 35,
  "parameters": {
    "strategy": "algebraic_lemmas",
    "max_runtime_seconds": 900,
    "model_profile": "local_prover"
  }
}
```

### F-14.05 Erkennung konkurrierender Kommandos

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.04
- Quelle: UI §10.2 (`expected_state_version`), §18.2 (Commands gleichzeitig)
- Bearbeiter: offen · Nachweise: offen

Stimmt `expected_state_version` nicht mit dem aktuellen Stand überein, wird das Kommando mit Versionskonflikt abgelehnt und der Client lädt den neuesten Zustand.

- [ ] Zwei gleichzeitige Kommandos auf denselben Stand ergeben genau eine Ausführung und einen Konflikt.

### F-14.06 Artefaktverweise statt großer Payloads

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.03, F-02.07
- Quelle: UI §16.4 (letzter Absatz), §17.2, §18.2 (große Events)
- Bearbeiter: offen · Nachweise: offen

Payloads oberhalb einer konfigurierten Größe werden im Artefaktspeicher abgelegt. Der Stream überträgt nur die Artefakt-ID.

- [ ] Ein Event mit großem Lean-Log enthält im Stream nur die ID, das Artefakt ist über F-14.02 abrufbar.

### F-14.07 Verhalten bei Verbindungs- und Komponentenausfällen

- Status: `ready` · Priorität: P0 · Meilenstein: M1
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

- Status: `ready` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-14.03
- Quelle: UI §15.2
- Bearbeiter: offen · Nachweise: offen

WebSockets werden erst eingeführt, wenn eine konkrete Interaktion wie Kollaboration sie benötigt.

- [ ] Der Bedarf ist in einem ADR begründet, bevor implementiert wird.

### F-14.11 Interner Research Event Bus

- Status: `review` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.03, F-00.01 (OD-04)
- Quelle: UI §15.1, §15.2 (interne Backend-Kommunikation)
- Bearbeiter: Claude · Nachweise: `src/mathlab/bus.py`, `tests/test_bus.py`. Am 2026-11-27 liefen `ruff format --check`, `ruff check` und `mypy` (strict) ohne Befund, `pytest` mit 914 passed und 56 skipped. Der Postgres-Test `test_redelivery_against_postgres_persists_once` wurde übersprungen, weil `MATHLAB_TEST_DATABASE_URL` nicht gesetzt war. Er ist vor `done` nachzuholen.

Agenten, CAS und Solver veröffentlichen Ergebnisse über einen Bus oder eine Queue. Der Bus schreibt in den Event Store und speist den Live-Stream, der Orchestrator abonniert ihn. Die Wahl der Technik folgt OD-04.

- [x] Ein Event wird genau einmal persistiert, auch wenn der Bus es mehrfach zustellt.

Referenzbeispiel aus UI §15.1, unverändert zitiert. Bei Abweichung gilt die Quelle.

```mermaid
flowchart TD
    A["Proof Agents / CAS / Solver"]
    B["Research Event Bus"]
    C["Event Store / PostgreSQL"]
    D["Live Stream API"]
    E["Research UI"]
    F["Control API"]
    G["Research Orchestrator"]

    A --> B
    B --> C
    B --> D
    D --> E
    E --> F
    F --> G
    G --> A
    G --> B
```
