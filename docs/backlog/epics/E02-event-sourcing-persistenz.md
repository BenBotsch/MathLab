# E02 Event Sourcing und Persistenz

- Status: `in-progress` · Meilenstein: M1
- Quellen: ARCH §4.2 (Event Sourcing), §9.4, §17.2, §18.4; UI §8.1, §9.3, §15, §16.1, §16.2, §17.2, §18.2 (Epic UI-01)
- Abhängige Epics: E00, E01

## Ziel

Alle Versuche und Entscheidungen werden als append-only Ereignisse gespeichert. Aktuelle Zustände, Dashboards und Replay entstehen aus Ereignissen und Snapshots. Große Artefakte liegen getrennt und werden per ID referenziert.

## Abgrenzung

Die HTTP- und SSE-Schnittstellen liegen in E14, die Replay-Oberfläche in E19.

## Invarianten

Ereignisse werden nie geändert oder gelöscht. Die Reihenfolge pro Run vergibt der Server. Verarbeitung ist idempotent.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-02.01 | Event-Envelope-Schema | `done` | P0 | M1 |
| F-02.02 | Eventtyp-Katalog | `done` | P0 | M1 |
| F-02.03 | Append-only Event Store | `done` | P0 | M1 |
| F-02.04 | Idempotenz und Deduplizierung | `done` | P0 | M1 |
| F-02.05 | Projektionen | `done` | P0 | M1 |
| F-02.06 | Snapshots und deterministisches Replay | `done` | P0 | M1 |
| F-02.07 | Artefaktspeicher | `done` | P0 | M1 |
| F-02.08 | Integrationstests für Reconnect und Absturz | `done` | P0 | M1 |
| F-02.09 | Schema-Versionierung und Migration | `ready` | P1 | M2 |
| F-02.10 | Ereignisse für Fortsetzen und Agentenende | `ready` | P1 | M2 |

## Features

### F-02.01 Event-Envelope-Schema

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: UI §16.1, §16.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat(core): add event envelope schema` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` (359 passed), alle ohne Befund. Modell in `src/mathlab/core/event.py`, Schema in `schemas/core/EventEnvelope.schema.json`, Tests in `tests/core/test_event.py`. Annahme: IDs sind UUIDs wie im übrigen Domänenmodell, die String-IDs aus UI §16.1 gelten als illustrativ.

Einheitlicher Umschlag mit den Pflichtfeldern `event_id`, `sequence`, `timestamp`, `type`, `schema_version`, `run_id`, `trace_id` und `payload` sowie den optionalen Feldern `problem_id`, `agent_id`, `proof_node_id`, `parent_event_id`, `verification_artifact_id` und `privacy_classification`.

- [x] Pydantic-Modell und JSON-Schema sind vorhanden.
- [x] Ein Event ohne Pflichtfeld wird abgelehnt.

Referenzbeispiel aus UI §16.1, unverändert zitiert. Bei Abweichung gilt die Quelle.

```json
{
  "event_id": "evt-008421",
  "sequence": 142,
  "timestamp": "2026-11-21T14:32:16Z",
  "type": "proof.step.verified",
  "run_id": "run-0042",
  "problem_id": "problem-0007",
  "agent_id": "induction-agent-01",
  "trace_id": "trace-8021",
  "parent_event_id": "evt-008419",
  "payload": {
    "proof_node_id": "node-0045",
    "method": "mathematical_induction",
    "verification_engine": "lean4",
    "verification_status": "VERIFIED",
    "duration_ms": 127
  }
}
```

### F-02.02 Eventtyp-Katalog

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.01
- Quelle: ARCH §9.4; UI §8.1
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat(core): add event type catalogue with payload schemas` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` (445 passed), alle ohne Befund. Katalog in `src/mathlab/core/event_types.py`, generierte Referenz in [docs/reference/event-types.md](../../reference/event-types.md) mit Drift-Test, Tests in `tests/core/test_event_types.py`. Annahme: Die Quellen nennen keine Payloads; die Schemas sind minimal und enthalten vor allem IDs. Verifikationsereignisse verlangen eine `verification_result_id`.

Vereinigung der Eventtypen beider Quellen mit Payload-Schema je Typ, darunter `problem.created`, `problem.formalized`, `strategy.selected`, `proof.attempt.started`, `proof.branch.created`, `proof.goal.created`, `proof.step.proposed`, `proof.step.accepted`, `proof.step.verified`, `proof.step.rejected`, `lemma.discovered`, `lemma.verified`, `hypothesis.created`, `counterexample.found`, `symbolic.calculation.completed`, `simulation.sample.received`, `proof.completed`, `proof.verification.failed`, `experiment.completed`, `knowledge.updated`, `model.trained`, `agent.started`, `budget.updated`, `run.paused` und `run.completed`.

- [x] Jeder Typ hat ein Payload-Schema und einen Beispieltest.
- [x] Die Liste ist in `docs/` als Referenz generiert oder gepflegt.
- [x] `proof.step.accepted` (ARCH) und `proof.step.verified` (UI) sind in ihrer Bedeutung voneinander abgegrenzt dokumentiert.

### F-02.03 Append-only Event Store

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.01, F-00.04
- Quelle: ARCH §9.4, §17.2; UI §9.3, §17.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat(storage): add append-only event store` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` gegen PostgreSQL 17.6 im Container (`MATHLAB_TEST_DATABASE_URL` gesetzt, 501 passed) und ohne Datenbank (491 passed, 10 übersprungen), alle ohne Befund. Store in `src/mathlab/storage/events.py`, Tests in `tests/storage/test_events.py`. Belege: 8 parallele Schreiber mit je 25 Ereignissen erhalten die Sequenzen 1 bis 200 ohne Lücke und ohne Doppelung. Ein abgelehntes Ereignis verbraucht keine Nummer. `UPDATE`, `DELETE` und `TRUNCATE` scheitern an Triggern mit `insufficient_privilege`. `read(run_id, after_sequence)` liefert die späteren Ereignisse geordnet. Annahmen: Die Sequenz vergibt eine Zählerzeile pro Run im selben Transaktionsschritt, nicht eine PostgreSQL-Sequence, weil diese Lücken erzeugt. Payloads werden beim Schreiben gegen F-02.02 und die Inline-Grenze aus ADR-0006 geprüft. Ein doppeltes `event_id` schlägt bis F-02.04 mit `UniqueViolation` fehl. Die Datenbanktests laufen nur mit gesetzter Variable, die CI braucht dafür einen PostgreSQL-Dienst (F-00.05).

PostgreSQL-Tabelle für Ereignisse mit monotoner Sequenznummer pro Run, vergeben durch den Server. Update und Delete sind auf Datenbankebene verhindert.

- [x] Parallele Schreiber erzeugen lückenlose, eindeutige Sequenzen pro Run.
- [x] `UPDATE` und `DELETE` auf der Tabelle schlagen fehl.
- [x] Nachladen ab einer Sequenznummer liefert alle späteren Ereignisse in Reihenfolge.

### F-02.04 Idempotenz und Deduplizierung

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.03
- Quelle: ARCH §18.4; UI §17.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat(storage): deduplicate events and apply projections idempotently` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` gegen PostgreSQL 17.6 im Container (507 passed) und ohne Datenbank (494 passed, 13 übersprungen), alle ohne Befund. Belege: Ein erneut eingereichtes Ereignis liefert das gespeicherte zurück und steht einmal im Store, auch bei 8 gleichzeitigen Einreichungen. Ein `event_id` mit anderem Inhalt löst `EventIdConflictError` aus. Ein Duplikat verbraucht keine Sequenznummer. `ProjectionRunner` (`src/mathlab/storage/projection.py`) wendet jedes Ereignis pro `(run_id, sequence)` genau einmal an, dreifaches Nachlesen des Logs lässt die Projektion unverändert, eine Lücke löst `SequenceGapError` aus. Abgrenzung: Die Deduplizierung über `command_id` gehört zur Command API und ist in F-14.04 als Akzeptanzkriterium belegt. Der Fortschritt des Runners liegt im Speicher, die dauerhafte Ablage folgt mit den Projektionen (F-02.05).

Doppelt eingereichte Ereignisse und Commands werden über `event_id` bzw. `command_id` erkannt und nur einmal angewendet.

- [x] Ein doppelt gesendetes Ereignis erscheint einmal im Store.
- [x] Projektionen bleiben bei erneuter Verarbeitung unverändert.

### F-02.05 Projektionen

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.02, F-02.03
- Quelle: ARCH §9.4; UI §15.3
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: add projections for run state, proof graph, agents and metrics` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` gegen PostgreSQL 17.6 im Container (514 passed) und ohne Datenbank (500 passed, 14 übersprungen), alle ohne Befund. Projektionen in `src/mathlab/projections.py`, Tests in `tests/test_projections.py`. Beleg: Zwei verschränkte Runs werden nach jedem Ereignis mit erneuter Zustellung aller bisherigen Ereignisse live projiziert. Der Zustand stimmt nach jedem Schritt mit `rebuild` aus dem Log überein, auch beim Nachladen aus dem PostgreSQL-Store. Annahmen: Die Projektionen liegen im Speicher, dauerhafte Snapshots folgen mit F-02.06. Ein Knoten wird nur über `proof.step.verified` mit `verification_result_id` zu `VERIFIED`. Weil `run.resumed` und ein Ende-Ereignis für Agenten fehlen, setzt ein späteres Ereignis einen pausierten Run fort, und Agenten übernehmen ihren Endstatus aus `run.completed`. Die Lücke ist als F-02.10 erfasst.

Materialisierte Ansichten für Run-Zustand, Proof-Graph, Agentenzustände und Metriken, berechnet aus Ereignissen.

- [x] Neuaufbau aller Projektionen aus dem Event-Log ergibt denselben Zustand wie die laufende Projektion.

### F-02.06 Snapshots und deterministisches Replay

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.05
- Quelle: UI §9.3, §17.2, §20 (Kriterium 5)
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat(storage): add snapshots and deterministic replay` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` gegen PostgreSQL 17.6 im Container (519 passed) und ohne Datenbank (504 passed, 15 übersprungen), alle ohne Befund. Snapshots in `src/mathlab/storage/snapshots.py`, Tests in `tests/storage/test_snapshots.py`. Belege: Ein Property-Test mit Hypothesis (neue Entwicklungsabhängigkeit) erzeugt 150 zufällige gültige Ereignisfolgen über alle vier Projektionen, Snapshot-Intervalle von 1 bis 7 und ein zufälliges n. `replay` bis n ergibt jeweils denselben Zustand wie `rebuild` der ersten n Ereignisse. Derselbe Vergleich läuft mit Snapshots aus PostgreSQL für jedes n. `ReplayedState` nennt `sequence`, `snapshot_version` und `snapshot_sequence`. Annahmen: `SnapshottingRunner` legt alle `interval` Ereignisse pro Run einen Snapshot an. Ein Snapshot mit anderer Formatversion wird ignoriert und durch volles Replay ersetzt. Snapshots sind abgeleitete Daten, erneutes Speichern derselben Sequenz ändert nichts.

Regelmäßige konsistente Snapshots pro Run. Der Zustand zu einem beliebigen Zeitpunkt entsteht aus dem letzten Snapshot davor und den folgenden Ereignissen.

- [x] Replay bis Sequenz n ergibt denselben Zustand wie Live-Verarbeitung bis n (Property-Test).
- [x] Snapshot-Version und Sequenz sind im Zustand ablesbar.

### F-02.07 Artefaktspeicher

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.01 (OD-06), F-01.02
- Quelle: ARCH §17.1, §17.2; UI §16.4, §17.2, §18.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat(storage): add content-addressed artifact store` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` (465 passed), alle ohne Befund. Speicher in `src/mathlab/storage/artifacts.py`, Tests in `tests/storage/test_artifacts.py`. Die Größengrenze prüft `enforce_inline_limit` (Standard 16 KiB, konfigurierbar). Annahme: Der Medientyp wird geprüft, aber erst mit F-02.03 in der Datenbank gespeichert.

Ablage für Lean-Dateien, Solver- und Toollogs, Simulationsdaten und Grafiken, adressiert über Content-Hash. Ereignisse enthalten nur Artefakt-IDs.

- [x] Gleiches Artefakt wird nur einmal gespeichert.
- [x] Ein Ereignis mit großem Inhalt wird abgewiesen, wenn es keine Artefakt-ID verwendet (Größengrenze konfigurierbar).

### F-02.08 Integrationstests für Reconnect und Absturz

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.06
- Quelle: UI §18.2, §20 (Kriterium 4), §21 (Epic UI-01)
- Bearbeiter: Claude (Agent) · Nachweise: Commit `test(storage): add crash, restart and reconnect integration tests` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` gegen PostgreSQL 17.6 im Container (522 passed, die Recovery-Tests zusätzlich dreimal hintereinander grün) und ohne Datenbank (504 passed, 18 übersprungen), alle ohne Befund. Tests in `tests/storage/test_recovery.py`, Schreibprozess in `tests/storage/crash_writer.py`. Belege: Ein Unterprozess schreibt Ereignisse und wird mitten im Run hart beendet (`kill`). Jedes bestätigte Ereignis ist danach gespeichert, die Sequenz hat keine Lücke. Ein zweiter Prozess setzt denselben Run mit `resume` aus dem letzten Snapshot und den folgenden Ereignissen fort, die Sequenz läuft lückenlos weiter, und der Zustand stimmt mit dem Neuaufbau überein. Eine mit `pg_terminate_backend` getrennte Verbindung mitten in `append` hinterlässt keine Lücke, ein Leser lädt verpasste Ereignisse ab der letzten Sequenz nach. Neu im Code: `resume` und der Parameter `start` von `SnapshottingRunner` in `src/mathlab/storage/snapshots.py`. Der Reconnect über SSE folgt in F-14.07.

Tests für Backend-Neustart mitten im Run, verlorene Verbindungen und Wiederaufnahme ab der letzten Sequenz.

- [x] Nach einem simulierten Absturz fehlt kein abgeschlossenes Ereignis.
- [x] Ein Run wird nach Neustart aus Snapshot und Ereignissen fortgesetzt.

### F-02.09 Schema-Versionierung und Migration

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-02.02
- Quelle: UI §16.2, §16.4 (API-Schema versionieren)
- Bearbeiter: offen · Nachweise: offen

Regeln für kompatible und inkompatible Änderungen an Eventschemas. Alte Ereignisse bleiben lesbar.

- [ ] Ein Ereignis mit älterer `schema_version` wird korrekt projiziert.

### F-02.10 Ereignisse für Fortsetzen und Agentenende

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-02.05
- Quelle: ARCH §9.4; UI §10.1 (Start / Pause / Resume / Stop)
- Bearbeiter: offen · Nachweise: offen

Beim Umsetzen von F-02.05 aufgefallen: Der Katalog kennt `run.paused`, aber kein `run.resumed`, und `agent.started`, aber kein Ende-Ereignis für Agenten. Die Projektionen leiten Fortsetzen und Agentenende deshalb ab. Die fehlenden Ereignistypen werden ergänzt und die Projektionen auf sie umgestellt.

- [ ] `run.resumed` und ein Ende-Ereignis für Agenten mit Endstatus stehen im Katalog und in der Referenz.
- [ ] Run- und Agentenprojektion verwenden die neuen Ereignisse statt der Ableitung.
