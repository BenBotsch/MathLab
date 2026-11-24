# E09 Trial-and-Error und Experiment Tracking

- Status: `in-progress` · Meilenstein: M1, Ausbau M2 und M4
- Quellen: ARCH §7.4, §9.1 bis §9.3, §10.1, §11.5; UI §12.1
- Abhängige Epics: E01, E02

## Ziel

Jeder Versuch wird vollständig und reproduzierbar gespeichert, auch der gescheiterte. Fehler werden klassifiziert, damit das System aus negativen Ergebnissen lernt und Wiederholungen vermeidet. Workflow D aus ARCH §7.4 schließt jeden Run mit Auswertung und Lernschritt ab.

## Abgrenzung

Lernverfahren auf diesen Daten liegen in E12, die Metrik-Dashboards in E21, der Beweisbericht in E13. Der Eventtyp-Katalog liegt in F-02.02.

## Invarianten

Kein Versuch wird gelöscht. Ein ProofAttempt ohne Pflichtfelder wird nicht gespeichert. Negative Evidenz gilt nur im Kontext, in dem sie entstand (ARCH §9.3). Training und Produktivbetrieb sind entkoppelt (ARCH §7.4).

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-09.01 | ProofAttempt-Modell | `done` | P0 | M1 |
| F-09.02 | Pflichtfelder pro Versuch | `done` | P0 | M1 |
| F-09.03 | Fehlerkatalog und Klassifizierer | `done` | P0 | M1 |
| F-09.04 | Kontextuelle negative Evidenz | `ready` | P1 | M2 |
| F-09.05 | Run-Metriken | `ready` | P0 | M1 |
| F-09.06 | Workflow D Nachbearbeitung und Lernen | `todo` | P1 | M2 |
| F-09.07 | Metrik für verifizierten Fortschritt | `todo` | P1 | M4 |

## Features

### F-09.01 ProofAttempt-Modell

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02, F-02.03
- Quelle: ARCH §9.1
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: rebuild proof attempts from events` auf `develop`. Am 2026-11-23 gelaufen: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` mit PostgreSQL (537 passed) und ohne (518 passed, 19 übersprungen). `ProofAttemptProjection` und `rebuild_attempts` in `src/mathlab/attempts.py`, Tests in `tests/test_attempts.py`: Das Quellbeispiel wird aus Ereignissen ab `proof.attempt.started` vollständig rekonstruiert, auch nach Speicherung im Event Store; `lineage` und `children` fragen die Kette über `parent_attempt_id` ab, auch über Runs hinweg, Zyklen werden gemeldet. Entscheidung des Benutzers am 2026-11-23: neuer Eventtyp `proof.attempt.finished` (Suche, Ressourcen, Schätzwerte, `next_actions`) und optionale Felder an `proof.attempt.started`, dokumentiert in `docs/reference/event-types.md`. Abweichungen von der Quelle: `PARTIAL` erscheint als `OPEN` mit `valid_steps > 0`, weil Verifikationsstatus und Fortschritt getrennt sind; `terminal_success` wird aus `proof.completed` abgeleitet und kann nicht vom Agenten gesetzt werden; gültige und ungültige Schritte werden aus den Schrittereignissen gezählt. IDs sind UUIDs statt `ATTEMPT-…`.

`ProofAttempt` mit den Feldern aus ARCH §9.1: `id`, `problem_id`, `parent_attempt_id`, `agent` (`id`, `version`), `model` (`name`, `version`), `strategy` (`id`, `parameters`), `search` (`state_before`, `state_after`, `generated_lemmas`), `verification` (`status`, `valid_steps`, `invalid_steps`, `unresolved_goals`), `resources` (`duration_ms`, `input_tokens`, `output_tokens`), `evaluation` (`terminal_success`, `verified_progress`, `novelty`, `estimated_solvability`) und `next_actions`. Die Zahlenwerte im Quellbeispiel sind reine Beispieldaten.

- [x] Ein Versuch ist aus Ereignissen ab `proof.attempt.started` vollständig rekonstruierbar.
- [x] Die Kette über `parent_attempt_id` ist abfragbar.

Referenzbeispiel aus ARCH §9.1, unverändert zitiert. Bei Abweichung gilt die Quelle.

```yaml
proof_attempt:
  id: ATTEMPT-00851
  problem_id: PROBLEM-00042
  parent_attempt_id: ATTEMPT-00849
  agent:
    id: induction_agent
    version: 1.2.0
  model:
    name: local_prover
    version: 0.4.2
  strategy:
    id: proof.induction.natural_numbers
    parameters:
      max_depth: 20
  search:
    state_before: STATE-552
    state_after: STATE-553
    generated_lemmas: [LEMMA-202]
  verification:
    status: PARTIAL
    valid_steps: 4
    invalid_steps: 1
    unresolved_goals: 2
  resources:
    duration_ms: 1420
    input_tokens: 1200
    output_tokens: 480
  evaluation:
    terminal_success: false
    verified_progress: 0.42
    novelty: 0.18
    estimated_solvability: 0.65
  next_actions:
    - investigate_remaining_goal
```

### F-09.02 Pflichtfelder pro Versuch

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-09.01, F-00.03
- Quelle: ARCH §9.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: require ARCH 9.2 protocol fields for proof attempts` auf `develop`. Am 2026-11-24 gelaufen: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` mit PostgreSQL (604 passed) und ohne (584 passed, 20 übersprungen). Pflichtfelder in `src/mathlab/core/attempt_protocol.py` (`AttemptSetup`: Environment samt Fingerprint, Modell mit Gewichten, Promptversion, Quantisierung und Parametern, Datensatz- und Benchmarkversion, Seed, Hardware, Budget) und als Pflichtfelder der Payloads von `proof.attempt.started`, `proof.attempt.finished`, `proof.step.proposed`, `proof.step.verified` und `proof.step.rejected`; die Zuordnung jedes ARCH-§9.2-Punkts steht im Moduldocstring. `tests/test_attempts.py` entfernt jedes Pflichtfeld einzeln und erwartet die Ablehnung, der Event Store speichert einen solchen Versuch nicht. `repeat_setup` liefert die gespeicherte Konfiguration nur bei identischem Environment und nennt sonst die abweichenden Felder, belegt auch nach Speicherung in PostgreSQL. Annahmen: Nicht anwendbare oder nicht gemessene Werte (Benchmark, Quantisierung, Tokens, Speicher) sind Pflichtschlüssel mit explizitem `null`. Kosten werden nach ADR-0003 als Modellaufrufe und Tokens geführt, nicht in Währung. Child-Verknüpfungen werden aus `parent_attempt_id` abgeleitet (`children`). `failure_code` bleibt optional bis F-09.03 (seit F-09.03 Pflichtschlüssel).

Zusätzlich zu F-09.01 werden die Felder aus ARCH §9.2 protokolliert.

- Toolchain-, Lean- und Mathlib-Version und Git-Commit
- Modellgewichte, Promptversion, Quantisierung, Parameter
- Datensatz- und Benchmarkversion
- Zufallsseed, Hardware und Ressourcenbudget
- Eingabe- und Ausgabe-Token, tatsächliche oder geschätzte Kosten
- Proof-State-Fingerprints vor und nach jedem Schritt
- Taktik oder Werkzeugaufruf und Rohantwort
- Validierungsresultat inklusive konkreter Fehlermeldung
- Provenienz sämtlicher herangezogener Theoreme und Daten
- Parent- und Child-Verknüpfungen aller Suchzweige
- Ausführungszeit, Speicherbedarf, Retry-Anzahl
- Stoppgrund, verbleibendes Budget und empfohlenes Folgeexperiment

- [x] Fehlt ein Pflichtfeld, wird der Versuch abgelehnt.
- [x] Ein gespeicherter Versuch lässt sich mit denselben Versionen wiederholen.

### F-09.03 Fehlerkatalog und Klassifizierer

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-09.01
- Quelle: ARCH §9.3
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: classify lean and tool failures into the ARCH 9.3 catalogue` auf `develop`. Am 2026-11-24 gelaufen: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` mit PostgreSQL (620 passed) und ohne (600 passed, 20 übersprungen). `src/mathlab/failures.py` enthält `FailureClass` (neun Klassen plus `UNCLASSIFIED`), `REACTIONS` (eine Reaktion je Klasse), den geordneten Regelklassifizierer `classify` und `FailureStats`, das Klassen zählt und nicht zugeordnete Ausgaben aufbewahrt. `tests/fixtures/failures/` enthält für jede Klasse eine echte Ausgabe von Lean v4.36.0 mit Mathlib `fc4f59e5` samt Eingabe; `tests/test_failures.py` klassifiziert jede davon. `proof.step.rejected` verlangt `failure_code` jetzt als Pflichtschlüssel, `null` steht für `UNCLASSIFIED`. Annahmen: `SEMANTIC_MISMATCH` ist nur beim Abgleich mit der bestätigten Zielaussage erkennbar und wird über `Stage.TARGET_CHECK` erkannt. Bei Überschneidungen entscheidet die Regelreihenfolge, etwa Suche erschöpft vor offenen Zielen.

Die neun Fehlerklassen aus ARCH §9.3 mit ihrer Reaktion. Ein Klassifizierer bildet Lean- und Toolfehler darauf ab, die Reaktion setzt F-08.07 um.

| Fehler | Reaktion |
| --- | --- |
| `SYNTAX_ERROR` | Generierung korrigieren |
| `TYPE_ERROR` | Statement und Typen inspizieren |
| `MISSING_LEMMA` | Retrieval oder Lemma-Erzeugung |
| `INVALID_INFERENCE` | Schritt zurücknehmen |
| `COUNTEREXAMPLE_FOUND` | Bedingungen korrigieren |
| `SEARCH_EXHAUSTED` | Verbleibende Suchalternativen markieren |
| `CIRCULAR_DEPENDENCY` | Abhängigkeitsgraph prüfen |
| `SEMANTIC_MISMATCH` | Formulierung prüfen |
| `RESOURCE_EXHAUSTION` | Budget oder Strategie anpassen |

- [x] Jede Klasse hat mindestens einen Testfall mit echtem Lean- oder Toolfehler.
- [x] Nicht zuordenbare Fehler landen in einer eigenen Klasse und werden gezählt. Diese Klasse ist eine Ergänzung des Backlogs.

### F-09.04 Kontextuelle negative Evidenz

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-09.03
- Quelle: ARCH §9.3 (letzter Absatz), §11.5, §7.4 (Schritt 4)
- Bearbeiter: offen · Nachweise: offen

Ein Fehlschlag wird mit Kontext gespeichert, also Problemklasse, Methode, Voraussetzungen, Budget und Modell. Eine Methode gilt nicht als grundsätzlich untauglich, weil ein Versuch mit kleinerem Budget oder falschen Voraussetzungen scheiterte. Die Daten speisen die negative Memory in F-10.08.

- [ ] Negative Evidenz wird nur bei passendem Kontext zur Vermeidung herangezogen (Test mit abweichendem Budget).

### F-09.05 Run-Metriken

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.05
- Quelle: ARCH §10.1; UI §12.1
- Bearbeiter: offen · Nachweise: offen

Projektion mit den Run-Kennzahlen aus UI §12.1: aktive und abgeschlossene Agenten, Proof Attempts und Suchzweige, formal verifizierte Lemmata und Beweise, offene Beweispflichten, CPU-, GPU-, Speicher- und Tokenverbrauch, Time to First Valid Lemma, Time to Proof, Solver-Fehlerrate und Retry-Anzahl. Die geschätzte Lösbarkeit kommt aus F-12.03 und ist als Schätzung gekennzeichnet.

- [ ] Metriken stimmen mit einer Neuberechnung aus dem Event-Log überein.
- [ ] Fehlerquoten sind pro Fehlerklasse aus F-09.03 verfügbar.

### F-09.06 Workflow D Nachbearbeitung und Lernen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-09.04, F-09.05, F-10.03
- Quelle: ARCH §7.4
- Bearbeiter: offen · Nachweise: offen

Die sechs Schritte aus ARCH §7.4 laufen nach jedem Run.

1. Erfolgsstatus und alle Metriken ermitteln.
2. Alternativen vergleichen nach korrekten Schritten, Länge, Rechenaufwand, Methoden und Beweisstruktur.
3. Neue verifizierte Lemmata und Beziehungen in den Wissensgraphen aufnehmen (F-10.03).
4. Fehlschläge als kontextspezifische Erkenntnisse speichern (F-09.04).
5. Replay-Daten für spätere Trainingsläufe markieren, ohne Training im Produktivbetrieb auszulösen (F-12.08).
6. Beweisbericht mit Erläuterungen, Formeln und Visualisierungen anstoßen (F-13.04).

- [ ] Nach Abschluss eines Runs liegen für alle sechs Schritte Ereignisse oder Artefakte vor.
- [ ] Das Markieren von Replay-Daten verändert keine Modellgewichte.

### F-09.07 Metrik für verifizierten Fortschritt

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-09.05, F-12.01
- Quelle: ARCH §9.1 (Hinweis), §10.1 (Warnung)
- Bearbeiter: offen · Nachweise: offen

`verified_progress` ist eine eigene, modellierte und validierte Metrik. Sie wird nicht aus der Zahl offener Teilziele berechnet, weil eine gute Zerlegung die Zahl offener Ziele erhöhen kann.

- [ ] Die Metrik steigt nur bei verifizierten Teilzielen (Test mit nicht verifizierten Vorschlägen).
- [ ] Eine Zerlegung mit mehr offenen Teilzielen senkt die Metrik nicht automatisch (Test).
- [ ] Die Validierung gegen historische Suchverläufe ist dokumentiert.
