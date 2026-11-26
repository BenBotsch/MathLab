# E03 Problem Engine

- Status: `in-progress` · Meilenstein: M1, Ausbau M2 und M5
- Quellen: ARCH §3.1, §4.1, §6.1 (Problem Classifier), §7.1, §11.4, §13.2, §21
- Abhängige Epics: E01, E04

## Ziel

Mathematische Probleme werden eingelesen, in eine kanonische versionierte Darstellung gebracht, formalisiert und klassifiziert. Die formale Aussage wird gegen die Originalaussage auf semantische Treue geprüft, weil ein formal gültiger Beweis einer falschen Formalisierung wertlos ist (ARCH §1.2, §13.1).

## Abgrenzung

Die Lean-Prüfung selbst liegt in E04. Retrieval und Wissensgraph liegen in E10.

## Invarianten

Die Originalaussage wird unverändert archiviert. Eine Formalisierung gilt erst nach bestandener Treueprüfung oder menschlicher Freigabe als Ziel.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-03.01 | Import von Text, LaTeX und Lean | `done` | P0 | M1 |
| F-03.02 | Kanonische Darstellung | `done` | P0 | M1 |
| F-03.03 | Mehrdeutigkeit protokollieren | `ready` | P1 | M1 |
| F-03.04 | Autoformalisierung | `todo` | P1 | M2 |
| F-03.05 | Prüfung der Statement Fidelity | `done` | P0 | M1 |
| F-03.06 | Problem Classifier | `ready` | P1 | M2 |
| F-03.07 | AST-Normalisierung und Fingerprints | `ready` | P1 | M2 |
| F-03.08 | Problemvarianten | `todo` | P1 | M2 |
| F-03.09 | Import von Papers und Datensätzen | `todo` | P2 | M5 |
| F-03.10 | Ereignis für Versionen der kanonischen Darstellung | `todo` | P1 | M1 |
| F-03.11 | Automatische Fidelity-Prüfung | `todo` | P1 | M2 |
| F-03.12 | Ereignis für die Fidelity-Prüfung | `todo` | P1 | M1 |

## Features

### F-03.01 Import von Text, LaTeX und Lean

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: ARCH §3.1, §7.1 (Schritt 1)
- Bearbeiter: Claude (Agent) · Nachweise: `src/mathlab/problem_import.py` (`ProblemInput`, `import_problem`, `original_input`) nimmt Text, LaTeX oder eine Lean-Aussage mit informellem Text an, legt die Originaleingabe byteweise im Artefaktspeicher ab und liefert `Problem` samt `problem.created`-Entwurf. `Problem` und `ProblemCreated` tragen dafür optional `input_format` und `original`. `tests/test_problem_import.py`: 8 bestanden, je Format Ereignis und unverändertes Original (auch Leerzeichen am Rand, `\r\n` und Unicode), auch nach erneutem Öffnen des Speichers. Schemas und `docs/reference/event-types.md` neu erzeugt. `ruff format`, `ruff check` und `mypy` (strict) ohne Befund; `pytest` mit Test-DB und allen Images 682 bestanden, ohne 650 bestanden, 32 übersprungen. Annahme: Der Lean-Code wird hier weder geparst noch geprüft, Formalisierung und Hash bleiben bei F-01.03 und E04.

Ein Problem kann als natürlicher Text, LaTeX oder Lean-Statement angelegt werden. In M1 reicht eine vorgegebene Lean-Aussage plus informeller Text.

- [x] Import erzeugt ein `Problem` und das Ereignis `problem.created`.
- [x] Die Originaleingabe ist unverändert abrufbar.

### F-03.02 Kanonische Darstellung

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-03.01, F-01.03, F-11.01
- Quelle: ARCH §3.1 (versionierte kanonische Darstellung), §7.1 (Schritt 2)
- Bearbeiter: Claude (Agent) · Nachweise: `src/mathlab/canonical.py` (`CanonicalContent`, `CanonicalForm`, `parse_lean`, `load_canonical`) erfasst Variablen mit Typ und Quantor, Voraussetzungen, Ziel, Geltungsbereich, Ausnahmen und Kontext. `CanonicalForm` ist unveränderlich und trägt einen Inhaltshash. `revise` erzeugt die nächste Version mit Verweis auf den Vorgänger und Änderungsgrund, eine Revision ohne Änderung wird abgewiesen. `benchmarks/golden/m1/canonical/v1.json` enthält die Darstellung aller 24 Golden-Aufgaben, aus den Lean-Aussagen abgeleitet. Nur der von Lean inferierte Typ von `p` in g20 ist von Hand als ℕ ergänzt. `tests/test_canonical.py`: 11 bestanden, darunter Vollständigkeit und Übereinstimmung mit der Lean-Aussage für jede Golden-Aufgabe sowie Versionierung, Hashprüfung und Unveränderlichkeit. `ruff format`, `ruff check` und `mypy` (strict) ohne Befund; `pytest` mit Test-DB und allen Images 704 bestanden, ohne 671 bestanden, 33 übersprungen. Annahmen: Der Parser deckt nur Signaturen im Stil der Golden-Liste ab, und Binder mit `h`-Präfix gelten als Voraussetzungen. Ein Ereignis für neue Versionen fehlt noch, siehe F-03.10.

Variablen, Quantoren, Typen, Geltungsbereiche, Ausnahmen und Voraussetzungen werden strukturiert erfasst und versioniert.

- [x] Für jede Golden-Aufgabe aus M1 ist die strukturierte Darstellung vollständig.
- [x] Jede Änderung erzeugt eine neue Version.

### F-03.03 Mehrdeutigkeit protokollieren

- Status: `ready` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-03.02
- Quelle: ARCH §7.1 (Schritt 3), §4.2 (Human Override)
- Bearbeiter: offen · Nachweise: offen

Erkannte Mehrdeutigkeiten werden mit Lesarten gespeichert. Ist sie relevant, wartet die Formalisierung auf eine menschliche Bestätigung.

- [ ] Ein mehrdeutiges Testproblem stoppt vor der Formalisierung mit einer offenen Rückfrage.

### F-03.04 Autoformalisierung

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.02, F-07.01, F-04.03
- Quelle: ARCH §7.1 (Schritt 4); ProofNet in ARCH §16.1
- Bearbeiter: offen · Nachweise: offen

Ein Modell erzeugt aus der kanonischen Darstellung eine Lean-Kandidatenaussage, die kompiliert.

- [ ] Kandidaten werden in Lean typgeprüft, bevor sie zur Treueprüfung gehen.
- [ ] Erfolgsquote auf einem festen Satz von Aufgaben wird gemessen (Semantic Formalization Accuracy, ARCH §16.3).

### F-03.05 Prüfung der Statement Fidelity

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-03.02
- Quelle: ARCH §7.1 (Schritt 5), §13.2, §21; SemantEq in ARCH §2.3
- Bearbeiter: Claude · Nachweise: `src/mathlab/core/fidelity.py` mit `FidelityReview`, Checkliste `CHECKLIST` (Variablen und Typen, Quantoren, Voraussetzungen, Ziel, Geltungsbereich, Ausnahmen, keine triviale Beweisbarkeit) und `require_approval`. `ConfirmedStatement.confirm` und `revise` verlangen eine freigebende Prüfung genau des neuen Inhalts (Formalisierungs-ID und Statement-Hash) und tragen ihre ID in `fidelity_review_id`. Ohne Prüfung, bei abgelehntem Punkt oder bei geändertem Inhalt entsteht kein Ziel-Hash (`FidelityError`). Eine Ablehnung braucht eine Begründung. Schema `schemas/core/ConfirmedStatement.schema.json` neu erzeugt. `tests/core/test_fidelity.py` mit 9 Tests, `tests/core/test_target.py` angepasst. `ruff format`, `ruff check`, `mypy` ohne Befund. `pytest` mit `MATHLAB_TEST_LEAN_IMAGE=mathlab-lean:latest`: 757 passed, 30 skipped (Datenbank-, Sandbox- und SymPy-Image fehlen). Das M2-Kriterium (automatische Erkennung einer Abschwächung als `SEMANTIC_MISMATCH`, zweite Formalisierung) ist nach F-03.11 verschoben.

Die formale Aussage wird gegen die Originalaussage geprüft. In M1 genügt eine menschliche Freigabe mit Checkliste. In M2 kommen eine zweite unabhängige Formalisierung und eine automatische Prüfung auf Abschwächung hinzu.

- [x] Ohne Freigabe erhält eine Formalisierung keinen Ziel-Hash.
- Das M2-Kriterium (abgeschwächte Testformalisierung als `SEMANTIC_MISMATCH`) steht in F-03.11.

### F-03.06 Problem Classifier

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.02
- Quelle: ARCH §3.1 (Klassifikation), §6.1, §7.1 (Schritt 6)
- Bearbeiter: offen · Nachweise: offen

Ordnet Problemen Gebiet, geeignete Methoden und geschätzte Komplexität zu. Erst regelbasiert und mit Sprachmodell, später als gelernter Klassifikator.

- [ ] Klassifikation wird gespeichert und von der Strategy Engine (F-06.06) gelesen.
- [ ] Trefferquote auf Golden Tasks mit bekannter Klasse ist gemessen.

### F-03.07 AST-Normalisierung und Fingerprints

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.02
- Quelle: ARCH §11.4
- Bearbeiter: offen · Nachweise: offen

Ausdrücke werden als AST gespeichert, gebundene Variablen konsistent umbenannt (Alpha-Äquivalenz), und kommutative oder assoziative Umformungen nur innerhalb passender algebraischer Strukturen angewendet. Daraus entstehen Struktur- und Abhängigkeits-Fingerprints.

- [ ] Alpha-äquivalente Aussagen haben denselben Fingerprint.
- [ ] Äquivalenz wird nur bei vorliegender Regel oder Beweis behauptet (Test mit nicht äquivalentem Gegenpaar).

### F-03.08 Problemvarianten

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.07
- Quelle: ARCH §18.1 (ProblemVariant), §16.4
- Bearbeiter: offen · Nachweise: offen

Varianten eines Problems werden als `ProblemVariant` mit Verweis auf das Ursprungsproblem geführt. Das dient der Robustheitsprüfung und der Leakage-Erkennung (F-11.08).

- [ ] Varianten sind mit Ursprung und Art der Änderung gespeichert.

### F-03.09 Import von Papers und Datensätzen

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-03.04, F-24.05
- Quelle: ARCH §3.1, §7.1 (Schritt 1)
- Bearbeiter: offen · Nachweise: offen

Import mathematischer Dokumente, Datensätze und Simulationsmodelle. Externe Inhalte gelten als nicht vertrauenswürdig.

- [ ] Ein Paper-Abschnitt wird als Problem mit Quellenverweis angelegt.

### F-03.10 Ereignis für Versionen der kanonischen Darstellung

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-03.02
- Quelle: ARCH §3.1, §7.1 (Schritt 2); beim Umsetzen von F-03.02 aufgefallen
- Bearbeiter: offen · Nachweise: offen

F-03.02 versioniert die kanonische Darstellung im Modell. Damit Versionen im Event Store landen und wiederhergestellt werden können, fehlt ein Ereignis wie `problem.canonicalized` samt Projektion.

- [ ] Jede neue Version erzeugt ein Ereignis, und die Projektion liefert die aktuelle und jede frühere Version.

### F-03.11 Automatische Fidelity-Prüfung

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.05, F-03.04
- Quelle: ARCH §7.1 (Schritt 5), §13.2, §21; SemantEq in ARCH §2.3; aus F-03.05 abgetrennt
- Bearbeiter: offen · Nachweise: offen

F-03.05 deckt in M1 die menschliche Freigabe mit Checkliste ab. In M2 kommen eine zweite unabhängige Formalisierung und eine automatische Prüfung auf Abschwächung hinzu. Ihr Ergebnis ergänzt die menschliche Prüfung und ersetzt sie nicht.

- [ ] Eine abgeschwächte Testformalisierung wird als `SEMANTIC_MISMATCH` erkannt.
- [ ] Weichen zwei unabhängige Formalisierungen voneinander ab, wird die Abweichung der Prüfung vorgelegt.

### F-03.12 Ereignis für die Fidelity-Prüfung

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-03.05
- Quelle: ARCH §7.1 (Schritt 5), §13.2; beim Umsetzen von F-03.05 aufgefallen
- Bearbeiter: offen · Nachweise: offen

F-03.05 hält die menschliche Prüfung nur im Modell fest (`FidelityReview`, `fidelity_review_id`). Damit jede Freigabe und Ablehnung im Event Store nachvollziehbar bleibt, fehlt ein Ereignis wie `statement.fidelity.reviewed` mit Formalisierungs-ID, geprüftem Statement-Hash, pseudonymer Prüfer-ID, Checkliste und Ergebnis.

- [ ] Jede Freigabe und jede Ablehnung erzeugt ein Ereignis, das auf die Formalisierung und den geprüften Hash verweist.
- [ ] Zu einer bestätigten Zielaussage lässt sich das Ereignis der Freigabe über `fidelity_review_id` finden.
