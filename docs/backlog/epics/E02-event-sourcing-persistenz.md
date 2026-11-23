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
| F-02.02 | Eventtyp-Katalog | `ready` | P0 | M1 |
| F-02.03 | Append-only Event Store | `todo` | P0 | M1 |
| F-02.04 | Idempotenz und Deduplizierung | `todo` | P0 | M1 |
| F-02.05 | Projektionen | `todo` | P0 | M1 |
| F-02.06 | Snapshots und deterministisches Replay | `todo` | P0 | M1 |
| F-02.07 | Artefaktspeicher | `ready` | P0 | M1 |
| F-02.08 | Integrationstests für Reconnect und Absturz | `todo` | P0 | M1 |
| F-02.09 | Schema-Versionierung und Migration | `todo` | P1 | M2 |

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

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.01
- Quelle: ARCH §9.4; UI §8.1
- Bearbeiter: offen · Nachweise: offen

Vereinigung der Eventtypen beider Quellen mit Payload-Schema je Typ, darunter `problem.created`, `problem.formalized`, `strategy.selected`, `proof.attempt.started`, `proof.branch.created`, `proof.goal.created`, `proof.step.proposed`, `proof.step.accepted`, `proof.step.verified`, `proof.step.rejected`, `lemma.discovered`, `lemma.verified`, `hypothesis.created`, `counterexample.found`, `symbolic.calculation.completed`, `simulation.sample.received`, `proof.completed`, `proof.verification.failed`, `experiment.completed`, `knowledge.updated`, `model.trained`, `agent.started`, `budget.updated`, `run.paused` und `run.completed`.

- [ ] Jeder Typ hat ein Payload-Schema und einen Beispieltest.
- [ ] Die Liste ist in `docs/` als Referenz generiert oder gepflegt.
- [ ] `proof.step.accepted` (ARCH) und `proof.step.verified` (UI) sind in ihrer Bedeutung voneinander abgegrenzt dokumentiert.

### F-02.03 Append-only Event Store

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.01, F-00.04
- Quelle: ARCH §9.4, §17.2; UI §9.3, §17.2
- Bearbeiter: offen · Nachweise: offen

PostgreSQL-Tabelle für Ereignisse mit monotoner Sequenznummer pro Run, vergeben durch den Server. Update und Delete sind auf Datenbankebene verhindert.

- [ ] Parallele Schreiber erzeugen lückenlose, eindeutige Sequenzen pro Run.
- [ ] `UPDATE` und `DELETE` auf der Tabelle schlagen fehl.
- [ ] Nachladen ab einer Sequenznummer liefert alle späteren Ereignisse in Reihenfolge.

### F-02.04 Idempotenz und Deduplizierung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.03
- Quelle: ARCH §18.4; UI §17.2
- Bearbeiter: offen · Nachweise: offen

Doppelt eingereichte Ereignisse und Commands werden über `event_id` bzw. `command_id` erkannt und nur einmal angewendet.

- [ ] Ein doppelt gesendetes Ereignis erscheint einmal im Store.
- [ ] Projektionen bleiben bei erneuter Verarbeitung unverändert.

### F-02.05 Projektionen

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.02, F-02.03
- Quelle: ARCH §9.4; UI §15.3
- Bearbeiter: offen · Nachweise: offen

Materialisierte Ansichten für Run-Zustand, Proof-Graph, Agentenzustände und Metriken, berechnet aus Ereignissen.

- [ ] Neuaufbau aller Projektionen aus dem Event-Log ergibt denselben Zustand wie die laufende Projektion.

### F-02.06 Snapshots und deterministisches Replay

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.05
- Quelle: UI §9.3, §17.2, §20 (Kriterium 5)
- Bearbeiter: offen · Nachweise: offen

Regelmäßige konsistente Snapshots pro Run. Der Zustand zu einem beliebigen Zeitpunkt entsteht aus dem letzten Snapshot davor und den folgenden Ereignissen.

- [ ] Replay bis Sequenz n ergibt denselben Zustand wie Live-Verarbeitung bis n (Property-Test).
- [ ] Snapshot-Version und Sequenz sind im Zustand ablesbar.

### F-02.07 Artefaktspeicher

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.01 (OD-06), F-01.02
- Quelle: ARCH §17.1, §17.2; UI §16.4, §17.2, §18.2
- Bearbeiter: offen · Nachweise: offen

Ablage für Lean-Dateien, Solver- und Toollogs, Simulationsdaten und Grafiken, adressiert über Content-Hash. Ereignisse enthalten nur Artefakt-IDs.

- [ ] Gleiches Artefakt wird nur einmal gespeichert.
- [ ] Ein Ereignis mit großem Inhalt wird abgewiesen, wenn es keine Artefakt-ID verwendet (Größengrenze konfigurierbar).

### F-02.08 Integrationstests für Reconnect und Absturz

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.06
- Quelle: UI §18.2, §20 (Kriterium 4), §21 (Epic UI-01)
- Bearbeiter: offen · Nachweise: offen

Tests für Backend-Neustart mitten im Run, verlorene Verbindungen und Wiederaufnahme ab der letzten Sequenz.

- [ ] Nach einem simulierten Absturz fehlt kein abgeschlossenes Ereignis.
- [ ] Ein Run wird nach Neustart aus Snapshot und Ereignissen fortgesetzt.

### F-02.09 Schema-Versionierung und Migration

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-02.02
- Quelle: UI §16.2, §16.4 (API-Schema versionieren)
- Bearbeiter: offen · Nachweise: offen

Regeln für kompatible und inkompatible Änderungen an Eventschemas. Alte Ereignisse bleiben lesbar.

- [ ] Ein Ereignis mit älterer `schema_version` wird korrekt projiziert.
