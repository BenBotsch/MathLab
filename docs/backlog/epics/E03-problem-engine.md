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
| F-03.02 | Kanonische Darstellung | `ready` | P0 | M1 |
| F-03.03 | Mehrdeutigkeit protokollieren | `todo` | P1 | M1 |
| F-03.04 | Autoformalisierung | `todo` | P1 | M2 |
| F-03.05 | Prüfung der Statement Fidelity | `todo` | P0 | M1 |
| F-03.06 | Problem Classifier | `todo` | P1 | M2 |
| F-03.07 | AST-Normalisierung und Fingerprints | `todo` | P1 | M2 |
| F-03.08 | Problemvarianten | `todo` | P1 | M2 |
| F-03.09 | Import von Papers und Datensätzen | `todo` | P2 | M5 |

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

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-03.01, F-01.03, F-11.01
- Quelle: ARCH §3.1 (versionierte kanonische Darstellung), §7.1 (Schritt 2)
- Bearbeiter: offen · Nachweise: offen

Variablen, Quantoren, Typen, Geltungsbereiche, Ausnahmen und Voraussetzungen werden strukturiert erfasst und versioniert.

- [ ] Für jede Golden-Aufgabe aus M1 ist die strukturierte Darstellung vollständig.
- [ ] Jede Änderung erzeugt eine neue Version.

### F-03.03 Mehrdeutigkeit protokollieren

- Status: `todo` · Priorität: P1 · Meilenstein: M1
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

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-03.02
- Quelle: ARCH §7.1 (Schritt 5), §13.2, §21; SemantEq in ARCH §2.3
- Bearbeiter: offen · Nachweise: offen

Die formale Aussage wird gegen die Originalaussage geprüft. In M1 genügt eine menschliche Freigabe mit Checkliste. In M2 kommen eine zweite unabhängige Formalisierung und eine automatische Prüfung auf Abschwächung hinzu.

- [ ] Ohne Freigabe erhält eine Formalisierung keinen Ziel-Hash.
- [ ] Eine abgeschwächte Testformalisierung wird als `SEMANTIC_MISMATCH` erkannt (M2-Kriterium).

### F-03.06 Problem Classifier

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.02
- Quelle: ARCH §3.1 (Klassifikation), §6.1, §7.1 (Schritt 6)
- Bearbeiter: offen · Nachweise: offen

Ordnet Problemen Gebiet, geeignete Methoden und geschätzte Komplexität zu. Erst regelbasiert und mit Sprachmodell, später als gelernter Klassifikator.

- [ ] Klassifikation wird gespeichert und von der Strategy Engine (F-06.06) gelesen.
- [ ] Trefferquote auf Golden Tasks mit bekannter Klasse ist gemessen.

### F-03.07 AST-Normalisierung und Fingerprints

- Status: `todo` · Priorität: P1 · Meilenstein: M2
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
