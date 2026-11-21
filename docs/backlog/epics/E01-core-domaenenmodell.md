# E01 Core-Domänenmodell und Contracts

- Status: `todo` · Meilenstein: M1
- Quellen: ARCH §1.2, §3.2, §3.3, §4.2, §18.1, §18.2, §18.4; UI §1.3, §3.2, §4.3
- Abhängige Epics: E00

## Ziel

Ein typisiertes Domänenmodell, das alle anderen Epics teilen. Es legt Statusräume, Kernentitäten, Provenienz und die Schnittstellen der Engines fest und macht die Invarianten aus [WORKFLOW.md](../WORKFLOW.md) im Code erzwingbar.

## Abgrenzung

Persistenz und Events liegen in E02. Konkrete Engine-Implementierungen liegen in E03 bis E08.

## Invarianten

`FORMALLY_VERIFIED` ist nur mit einem referenzierten `VerificationResult` erreichbar. Der Ziel-Hash einer bestätigten formalen Aussage ist unveränderlich.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-01.01 | Statusmaschine der Erkenntnisstufen | `todo` | P0 | M1 |
| F-01.02 | Kernentitäten als typisierte DTOs | `todo` | P0 | M1 |
| F-01.03 | Unveränderliche Zielaussage mit Hash | `todo` | P0 | M1 |
| F-01.04 | Engine-Contracts | `todo` | P0 | M1 |
| F-01.05 | Provenienzmodell | `todo` | P0 | M1 |
| F-01.06 | Run- und Betriebsmodusmodell | `todo` | P0 | M1 |
| F-01.07 | Getrennte Statusräume | `todo` | P0 | M1 |

## Features

### F-01.01 Statusmaschine der Erkenntnisstufen

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02
- Quelle: ARCH §1.2, §21 (strikte Statusmaschine)
- Bearbeiter: offen · Nachweise: offen

Die sieben Erkenntnisstufen mit erlaubten Übergängen und der jeweils nötigen Evidenz. Numerische Tests können eine Aussage höchstens auf `NUMERICALLY_SUPPORTED` heben.

- [ ] Übergänge sind als Tabelle im Code definiert und getestet.
- [ ] Ein Übergang zu `FORMALLY_VERIFIED` ohne `VerificationResult` wirft einen Fehler.
- [ ] Ein Übergang zu `REFUTED` verlangt ein Gegenbeispiel oder eine formale Widerlegung.

### F-01.02 Kernentitäten als typisierte DTOs

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02
- Quelle: ARCH §18.1
- Bearbeiter: offen · Nachweise: offen

Pydantic-Modelle für `Problem`, `ProblemVariant`, `FormalStatement`, `ProofState`, `ProofStep`, `ProofAttempt`, `SearchTrajectory`, `ProofMethod`, `VerificationResult`, `Lemma`, `Theorem`, `Counterexample`, `SimulationRun`, `Evidence`, `KnowledgeRelationship`, `AgentExecution`, `ModelVersion`, `EvaluationRun` und `PublicationSource`. Für M1 genügen die Felder, die E02, E04 und E09 brauchen. Weitere Felder kommen mit den jeweiligen Features.

- [ ] Alle genannten Entitäten existieren mit ID, Version und Zeitstempel.
- [ ] JSON-Schema-Export funktioniert und ist im Repo eingecheckt.

### F-01.03 Unveränderliche Zielaussage mit Hash

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: ARCH §4.2 (Immutable Target), §13.2, §18.4
- Bearbeiter: offen · Nachweise: offen

Die Originalaussage wird unveränderlich archiviert. Die bestätigte formale Aussage erhält einen Hash über normalisierten Lean-Text, Imports und Toolchain. Änderungen erzeugen eine neue Version mit neuem Hash und Provenienz.

- [ ] Ein Versuch, eine bestätigte Aussage zu ändern, scheitert.
- [ ] Der Hash ist reproduzierbar über Prozessgrenzen hinweg.

### F-01.04 Engine-Contracts

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: ARCH §18.2, §4.2 (Tool-Agnostic Contracts)
- Bearbeiter: offen · Nachweise: offen

Protocols für `ProofEngine`, `VerificationEngine`, `MathematicalRetriever`, `SearchPolicy`, `SymbolicEngine` und `SimulationEngine` mit typisierten DTOs, Timeout, Cancellation, Idempotenzschlüssel, Trace-ID, Fehlertypen und Versionsangabe.

- [ ] Jeder Contract hat eine Fake-Implementierung für Tests.
- [ ] Fehler sind typisiert und auf den Fehlerkatalog (F-09.03) abbildbar.

### F-01.05 Provenienzmodell

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: ARCH §3.2 (Nachvollziehbarkeit), §4.2 (Verified Reuse, Versioned Knowledge), §9.2
- Bearbeiter: offen · Nachweise: offen

Jede Behauptung trägt Quelle, Bedingungen, Prüfstatus, Artefakt-ID und Versionskontext. Herangezogene Theoreme werden mit exakter Bibliotheksreferenz geführt.

- [ ] Ein Lemma ohne Provenienz kann nicht gespeichert werden.
- [ ] Die Provenienz eines Lemmas ist bis zum Verifikationsartefakt rückverfolgbar.

### F-01.06 Run- und Betriebsmodusmodell

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: ARCH §3.3; UI §3.2
- Bearbeiter: offen · Nachweise: offen

Ein Run hat Problem, Modus, Konfiguration, Budget, Status und Zustandsversion. Die fünf Betriebsmodi sind als Enum mit den zugehörigen Zugriffsregeln definiert, deren Durchsetzung F-11.02 übernimmt.

- [ ] Run-Status-Übergänge `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, `CANCELLED` sind definiert und getestet.
- [ ] Jede Statusänderung erhöht die Zustandsversion.

### F-01.07 Getrennte Statusräume

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.01
- Quelle: UI §1.3, §4.3; ARCH §6.3
- Bearbeiter: offen · Nachweise: offen

Agentenstatus, Erkenntnisstufe, Verifikationsstatus, Run-Status und Proof-Knotenstatus sind getrennte Typen, wie in [glossary.md](../../glossary.md) beschrieben.

- [ ] Kein Typ lässt sich implizit in einen anderen umwandeln.
- [ ] Der Proof-Knotenstatus `VERIFIED` leitet sich nur aus einem `VerificationResult` ab.
