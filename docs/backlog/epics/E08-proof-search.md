# E08 Proof Search Engine

- Status: `in-progress` · Meilenstein: M1, Ausbau M2, M4 und M6
- Quellen: ARCH §2.1, §3.1, §4.1, §6.2 (Budget Controller), §7.2, §8; UI §4.1
- Abhängige Epics: E01, E02, E04, E07

## Ziel

Beweissuche als kontrollierte Exploration eines AND-OR-Hypergraphen mit Budgets, Checkpoints, Backtracking und Reparatur. Mehrere Suchverfahren sind austauschbar über den `SearchPolicy`-Contract.

## Abgrenzung

Gelernte Policy- und Value-Modelle liegen in E12. Die Darstellung des Graphen liegt in E16.

## Invarianten

Ein AND-Knoten gilt erst als gelöst, wenn alle Teilziele verifiziert sind. Ein OR-Knoten gilt als gelöst, wenn eine Alternative verifiziert ist. Jede Expansion verbraucht Budget und wird protokolliert.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-08.01 | Proof State und Aktionsraum | `done` | P0 | M1 |
| F-08.02 | AND-OR-Hypergraph | `done` | P0 | M1 |
| F-08.03 | Tiefen-, Breiten-, Best-First- und A*-Suche | `todo` | P0 | M1 |
| F-08.04 | Search Budget Controller | `ready` | P0 | M1 |
| F-08.05 | Checkpoint und Resume | `ready` | P0 | M1 |
| F-08.06 | Zerlegung und Backtracking | `todo` | P1 | M2 |
| F-08.07 | Reparatur und Strategiewechsel | `ready` | P1 | M2 |
| F-08.08 | Parallele Kandidaten und Beam Search | `todo` | P1 | M2 |
| F-08.09 | MCTS und HyperTree Proof Search | `todo` | P1 | M4 |
| F-08.10 | Alternative Beweise und Methodendiversität | `todo` | P1 | M2 |
| F-08.11 | Evolutionäre Suche und Counterexample-Guided Search | `todo` | P2 | M6 |

## Features

### F-08.01 Proof State und Aktionsraum

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.02, F-01.02
- Quelle: ARCH §8 (Einleitung)
- Bearbeiter: Claude · Nachweise: `src/mathlab/proof_state.py` mit `SearchState` (Ziele, Hypothesen, Hilfssätze, Abhängigkeiten), `ActionKind` mit den sechs Aktionsarten aus ARCH §8, `Action`, `root()` und `successor()`. Ein Nachfolger ist ein neuer, unveränderlicher Zustand mit `parent_id`, `action` und Tiefe, der Elternzustand bleibt unverändert. Der Fingerprint `sha256:<hex>` (Schema-Version 1) deckt nur den Inhalt ab: Gleicher Inhalt auf verschiedenen Wegen ergibt denselben Fingerprint, Mengen sind ordnungsunabhängig, die Zielreihenfolge zählt. Er wird beim Erzeugen geprüft. `tests/test_proof_state.py`: 13 Tests, Testlauf ohne Lean-Image 809 passed, 55 skipped. ruff, ruff format und mypy (strict) ohne Befund. Die Tactic Generator-Events nutzen weiterhin ihren eigenen Ziel-Hash; die Umstellung auf `SearchState` gehört zur Suche ab F-08.02.

Proof State s_t = (G_t, H_t, L_t, D_t) mit offenen Zielen, Hypothesen, verfügbaren Hilfssätzen und Abhängigkeiten. Aktionen sind Taktik, Umformung, neuer Hilfssatz, Fallzerlegung, Solveraufruf und Strategiewechsel.

- [x] Jede Aktion erzeugt einen neuen Zustand mit Elternverweis.
- [x] Jeder Zustand hat einen Fingerprint (vgl. F-09.02).

### F-08.02 AND-OR-Hypergraph

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-08.01
- Quelle: ARCH §8, §8.1; HTPS in ARCH §2.1; UI §4.1
- Bearbeiter: Claude · Nachweise: `src/mathlab/proof_graph.py` mit `ProofHypergraph` als Projektion des Eventlogs: Ziele sind OR-Knoten (`proof.goal.created`), Expansionen sind AND-Knoten (neues Event `proof.expansion.created`), Querkanten `DEPENDS_ON`, `REUSES` und `REFUTES` (neues Event `proof.relation.added`). Der Status wird bei jeder Abfrage von unten nach oben abgeleitet und nie gespeichert. `VERIFIED` entsteht nur aus `proof.step.verified`, `REFUTED` nur aus einem `REFUTES`-Verweis eines Gegenbeispiels mit `counterexample.checked` = `VERIFIED`; ein ungeprüftes Gegenbeispiel bleibt Evidenz. `DEPENDS_ON` hält einen Knoten bis zum Beweis des Hilfssatzes auf `WAITING`, Zyklen beweisen nichts. Eventkatalog und `docs/reference/event-types.md` sind erweitert. `tests/test_proof_graph.py`: 12 Tests, darunter AND-Knoten, OR-Knoten, `REFUTES` und Rekonstruktion aus Events. Testlauf ohne Lean-Image 827 passed, 55 skipped. ruff, ruff format und mypy (strict) ohne Befund.

Datenstruktur mit OR-Knoten für alternative Strategien und AND-Knoten für gemeinsam zu erfüllende Teilziele, dazu die Kanten `DEPENDS_ON`, `REUSES` und `REFUTES` aus UI §4.1. Statusweitergabe von unten nach oben.

- [x] Ein AND-Knoten ist erst gelöst, wenn alle Kinder verifiziert sind (Test).
- [x] Ein `REFUTES`-Verweis setzt das Ziel auf `REFUTED`, sobald das Gegenbeispiel exakt geprüft ist.
- [x] Der Graph ist aus Ereignissen rekonstruierbar.

### F-08.03 Tiefen-, Breiten-, Best-First- und A*-Suche

- Status: `todo` · Priorität: P0 · Meilenstein: M1, A* in M2
- Abhängigkeiten: F-08.02, F-01.04
- Quelle: ARCH §8.1
- Bearbeiter: offen · Nachweise: offen

Depth-First, Breadth-First und Best-First über den `SearchPolicy`-Contract, mit heuristischer Bewertung für Best-First. A* folgt, sobald eine Kostenschätzung existiert. Vor- und Nachteile laut ARCH §8.1 werden in der Konfiguration dokumentiert.

- [ ] Depth-First, Breadth-First und Best-First lösen die Odd-Sum-Aufgabe innerhalb des Budgets.
- [ ] A* ist mit einer dokumentierten Heuristik umgesetzt oder begründet zurückgestellt.

### F-08.04 Search Budget Controller

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-08.02
- Quelle: ARCH §8.2, §6.2 (Budget Controller), §6.1 (Meta Controller, erste Implementierung)
- Bearbeiter: offen · Nachweise: offen

Regelbasierter Controller nach ARCH §8.2.

- Eingaben: Problemkomplexität, bisheriger Erfolg, Value-Schätzung, Anzahl Iterationen, GPU- und CPU-Zeit, Tokenbudget, erwarteter Informationsgewinn, Wiederholungen.
- Aktionen: weitersuchen, Methode wechseln, ergänzende Lemmata abrufen, breiter explorieren, Budget erhöhen, pausieren, an Menschen eskalieren, beenden.
- Budgetstrategien: Stage-Limits, Cheap-First-Solver, parallele Kandidaten mit Stoppregel, Early Stopping, Task-Timeouts, Checkpoint und Resume, Priorisierung wiederverwendbarer Teilziele.

Budgetänderungen erzeugen `budget.updated`.

- [ ] Ein Run endet bei Budgetende kontrolliert mit Status und Stoppgrund.
- [ ] Jede der acht Aktionen ist mit Testfall belegt.
- [ ] Verbrauch pro Zweig ist abfragbar.

### F-08.05 Checkpoint und Resume

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-08.02, F-02.06
- Quelle: ARCH §8.2, §19 (Phase 2, pausierbar und wiederaufnehmbar); UI §10.1
- Bearbeiter: offen · Nachweise: offen

Suche kann pausiert und aus einem Snapshot fortgesetzt werden, ohne Zustand zu verlieren.

- [ ] Pause und Resume ergeben denselben Graph wie ein ununterbrochener Lauf mit gleichem Seed.

### F-08.06 Zerlegung und Backtracking

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-08.03, F-07.06
- Quelle: ARCH §3.1, §7.2 (Schritt 5)
- Bearbeiter: offen · Nachweise: offen

Zielzerlegung in Teilziele und Rückkehr zu früheren Zuständen, wenn ein Zweig scheitert. Gescheiterte Zweige bleiben im Graphen als `FAILED` oder `ABANDONED` sichtbar.

- [ ] Ein gescheiterter Zweig wird aufgegeben und ein alternativer Zweig verfolgt.

### F-08.07 Reparatur und Strategiewechsel

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-07.09, F-09.03
- Quelle: ARCH §7.2 (Schritt 5), §9.3 (Spalte Reaktion); Kimina in ARCH §2.1
- Bearbeiter: offen · Nachweise: offen

Lean-Fehler werden klassifiziert und je nach Fehlerklasse mit der Reaktion aus ARCH §9.3 beantwortet, also Reparaturversuch, Lemma-Abruf, Strategiewechsel oder Abbruch. Die Anzahl der Reparaturen ist begrenzt.

- [ ] Ein Beweis mit Tippfehler in einer Taktik wird nach Reparatur verifiziert.
- [ ] Die Reparaturgrenze wird eingehalten.
- [ ] Jede Fehlerklasse aus F-09.03 hat eine zugeordnete Reaktion.

### F-08.08 Parallele Kandidaten und Beam Search

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-08.03
- Quelle: ARCH §8.1, §8.2, §7.2 (Schritt 3); Seed-Prover in ARCH §2.1
- Bearbeiter: offen · Nachweise: offen

Mehrere Kandidaten pro Zustand werden parallel erzeugt und geprüft. Beam Search behält die k besten Zustände. Wegen des Risikos geringer Methodenvielfalt wird die Diversität mitgemessen.

- [ ] Parallelität ist konfigurierbar und im Budget berücksichtigt.
- [ ] Eine Stoppregel beendet parallele Kandidaten, sobald einer verifiziert ist.

### F-08.09 MCTS und HyperTree Proof Search

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-08.08, F-12.03
- Quelle: ARCH §8.1; HTPS in ARCH §2.1
- Bearbeiter: offen · Nachweise: offen

Monte-Carlo-Baumsuche und HyperTree Proof Search mit gelernter Policy und Value-Schätzung.

- [ ] Vergleich mit Best-First bei gleichem Budget ist dokumentiert (F-11.10).

### F-08.10 Alternative Beweise und Methodendiversität

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-08.06, F-06.03
- Quelle: ARCH §3.1, §3.3 (`ALTERNATIVE_PROOF`), §7.4 (Schritt 2), §15
- Bearbeiter: offen · Nachweise: offen

Nach einem ersten Beweis werden weitere unabhängige Beweise mit anderen Methoden gesucht. Diversität wird über Methoden und Struktur gemessen, unterschiedliche Texte gelten nicht automatisch als andere Beweise (UI §12.2).

- [ ] Für die Odd-Sum-Aufgabe werden der algebraische und der induktive Beweisweg gefunden und verifiziert (F-11.15).
- [ ] Ein Diversitätsmaß ist definiert und wird gespeichert.

### F-08.11 Evolutionäre Suche und Counterexample-Guided Search

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-08.08, F-05.06
- Quelle: ARCH §8.1
- Bearbeiter: offen · Nachweise: offen

Evolutionäre Suche für breite Variation von Strategien und Konstruktionen sowie Counterexample-Guided Search zum gezielten Verwerfen fehlerhafter Vermutungen. Evolutionäre Ergebnisse haben keinen automatischen Wahrheitsnachweis und gehen immer durch E04.

- [ ] Ein Konstruktionsproblem wird mit evolutionärer Suche gelöst und formal geprüft.
- [ ] Eine falsche Zwischenvermutung wird durch Counterexample-Guided Search verworfen.
