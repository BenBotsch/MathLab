# E20 Human-in-the-Loop

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §3.1, §21; UI §5.3, §10, §18.3, §20 (Stufe 1 und 2), §21 (Epic UI-07)
- Abhängige Epics: E07, E14, E15, E24

## Ziel

Menschen steuern laufende Forschung gezielt: Runs anhalten, Budgets ändern, Zweige priorisieren, Hinweise geben und neue Versuche anstoßen. Jede Aktion ist bestätigt, berechtigt und auditiert.

## Abgrenzung

Das Kommandoprotokoll mit `command_id` und `expected_state_version` liegt in F-14.04 und F-14.05. Rollen und Rechte liegen in F-24.03. Diese Epic definiert die einzelnen Kommandotypen, ihre Semantik und ihre Bedienung.

## Invarianten

Eine Schaltfläche zeigt einen neuen Zustand erst nach Backendbestätigung (UI §10.2). Kein Kommando überschreibt einen bestehenden Beweisverlauf, neue Versuche werden verknüpft (UI §10.3). Ein menschlicher Hinweis ist Evidenz und kein Beweis. Kein Kommando setzt einen Verifikationsstatus.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-20.01 | Pause, Resume und Stop | `todo` | P0 | M1 |
| F-20.02 | Budgetänderungen | `todo` | P1 | M1 |
| F-20.03 | Suchzweig priorisieren | `todo` | P1 | M2 |
| F-20.04 | Neuer verknüpfter Versuch | `todo` | P1 | M2 |
| F-20.05 | Mathematischer Hinweis als versioniertes Artefakt | `todo` | P1 | M2 |
| F-20.06 | Folgetask und Alternativmodell | `todo` | P1 | M2 |
| F-20.07 | Lemma erneut prüfen | `todo` | P1 | M2 |
| F-20.08 | Experimentparameter als neue Version | `todo` | P1 | M2 |
| F-20.09 | Bestätigung kostspieliger und destruktiver Aktionen | `todo` | P0 | M1 |
| F-20.10 | Berechtigungs- und Auditregeln | `todo` | P0 | M1 |
| F-20.11 | Eskalation an einen Menschen | `todo` | P1 | M2 |

## Features

### F-20.01 Pause, Resume und Stop

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.04, F-07.03, F-08.05
- Quelle: UI §10.1 (Run), §20 (Stufe 1, Kriterium 6), §21 (Epic UI-07)
- Bearbeiter: offen · Nachweise: offen

Kommandos `run.pause`, `run.resume` und `run.stop` als Zustandswechsel durch den Orchestrator. Pause sichert den Suchzustand über einen Checkpoint. Die Kommandonamen sind Vorschläge des Backlogs.

- [ ] Pausieren und Fortsetzen werden serverseitig bestätigt und vollständig protokolliert.
- [ ] Nach Resume läuft die Suche ab dem Checkpoint ohne Verlust weiter.

### F-20.02 Budgetänderungen

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-20.01, F-08.04
- Quelle: UI §18.3 (Budgetänderung), §21 (Epic UI-07)
- Bearbeiter: offen · Nachweise: offen

Budget eines Runs für Zeit, Token und Rechenressourcen erhöhen oder senken, begrenzt durch Quoten aus F-24.06.

- [ ] Eine Änderung über der Quote wird mit Begründung abgelehnt.

### F-20.03 Suchzweig priorisieren

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-20.02, F-08.04
- Quelle: UI §10.1 (Suchzweig, Priorität), §20 (Stufe 2, Suchzweig-Priorisierung)
- Bearbeiter: offen · Nachweise: offen

Priorität eines Suchzweigs erhöhen oder senken. Der Search Budget Controller verteilt das Budget entsprechend um.

- [ ] Die Umverteilung ist als Event mit altem und neuem Budget sichtbar.

### F-20.04 Neuer verknüpfter Versuch

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-20.03, F-09.01
- Quelle: UI §10.1 (Neue Methode hinzufügen), §10.3, §20 (Stufe 2, Kriterium 4)
- Bearbeiter: offen · Nachweise: offen

Kommando `branch.investigate` aus UI §16.3. Die `parameters` sind `strategy` für die Methode oder die zusätzlichen Hilfssätze, `max_runtime_seconds` für das Zeitbudget und `model_profile` für das Modell. Im Beispiel aus UI §10.3 entsprechen zusätzliche algebraische Hilfssätze `strategy: algebraic_lemmas`, 15 Minuten `max_runtime_seconds: 900` und das neue Modell `model_profile: local_prover`. Das vollständige Kommando steht in F-14.04. Es entsteht eine neue `branch_id` mit eigenem ProofAttempt, verknüpft mit dem Ausgangsknoten.

- [ ] Das Beispiel aus UI §10.3 (Induktionsschritt, neues Modell, 15 Minuten) erzeugt einen neuen, auditierbaren Attempt.
- [ ] Der vorhandene Beweisverlauf bleibt unverändert.

### F-20.05 Mathematischer Hinweis als versioniertes Artefakt

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-14.04, F-02.07, F-01.05
- Quelle: UI §5.3, §10.1 (Teilziel, Hinweis), §21 (Epic UI-07)
- Bearbeiter: offen · Nachweise: offen

Ein Hinweis zu einem Teilziel oder an einen Agenten wird als versioniertes Artefakt mit Autor und Provenienz gespeichert und in den Kontext neuer Versuche gegeben.

- [ ] Ein Hinweis hat höchstens die Erkenntnisstufe CONJECTURED, bis er formal geprüft ist.

### F-20.06 Folgetask und Alternativmodell

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-14.04, F-07.15
- Quelle: UI §5.3, §10.1 (Agent)
- Bearbeiter: offen · Nachweise: offen

Einen neuen versionierten Folgetask an einen Agenten senden oder einen neuen Agentenrun mit Alternativmodell starten. Die Historie bleibt unverändert.

- [ ] Ein Alternativmodell-Run ist mit dem ursprünglichen Agentenrun verknüpft.

### F-20.07 Lemma erneut prüfen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-14.04, F-04.06
- Quelle: UI §10.1 (Lemma, Erneut überprüfen)
- Bearbeiter: offen · Nachweise: offen

Ein neuer Verifikationslauf für ein Lemma, etwa nach einem Mathlib-Wechsel.

- [ ] Der neue Lauf erzeugt ein eigenes Verifikationsartefakt, das alte bleibt erhalten.

### F-20.08 Experimentparameter als neue Version

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-14.04, F-05.05
- Quelle: UI §10.1 (Experiment, Parameter ändern)
- Bearbeiter: offen · Nachweise: offen

Parameteränderungen an einem Experiment erzeugen eine neue Experimentversion.

- [ ] Ergebnisse beider Versionen bleiben getrennt abrufbar.

### F-20.09 Bestätigung kostspieliger und destruktiver Aktionen

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-20.01
- Quelle: UI §10.2 (letzter Absatz), §14.4, §18.3
- Bearbeiter: offen · Nachweise: offen

Run-Abbruch, große Budgeterhöhungen und Mehrfachaktionen verlangen eine ausdrückliche Bestätigung im Client.

- [ ] Stop ohne Bestätigung sendet kein Kommando (UI-Test).

### F-20.10 Berechtigungs- und Auditregeln

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.04, F-24.03
- Quelle: UI §18.3, §21 (Epic UI-07)
- Bearbeiter: offen · Nachweise: offen

Jedes Kommando wird gegen die Rolle des Absenders geprüft. Audit-Events enthalten Absender, Kommando, Parameter, Ergebnis und Zeitpunkt, aber keine Secrets.

- [ ] Ein Kommando ohne Berechtigung wird abgelehnt und als Audit-Event protokolliert.

### F-20.11 Eskalation an einen Menschen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-07.03, F-03.03
- Quelle: ARCH §21 (menschliches Review bei Formalisierung), UI §10
- Bearbeiter: offen · Nachweise: offen

Das System kann einen Menschen anfordern, etwa bei mehrdeutiger Formalisierung oder abweichenden unabhängigen Formalisierungen. Die Anfrage erscheint als Aufgabe in der Oberfläche und blockiert nur den betroffenen Zweig.

- [ ] Eine Eskalation ist als Event mit Grund und betroffenem Knoten sichtbar.
