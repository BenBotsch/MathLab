# E22 Workflow Builder und visuelle Orchestrierung

- Status: `todo` · Meilenstein: M6
- Quellen: ARCH §7, §8.2; UI §2.1 (Workflow Builder, P2), §13.5, §20 (Stufe 3), §21
- Abhängige Epics: E07, E08, E11, E15

## Ziel

Forschungsabläufe aus Startbedingungen, Modellen, Strategien, Agenten, Tools, Prüfschritten, Fehler-Workflows und Budgetlimits werden visuell erstellt, validiert, versioniert und reproduzierbar ausgeführt.

## Abgrenzung

Die festen Workflows A bis E aus ARCH §7 werden im Code in E03, E04, E05, E07 und E09 umgesetzt. Der Builder macht sie konfigurierbar, ersetzt sie aber nicht.

## Invarianten

Workflow-Kanten beschreiben Aufgabensteuerung und keine mathematischen Implikationen. Das Builder-Layout ist klar vom Proof Graph abgegrenzt (UI §13.5). Kein Workflow kann den Verifier umgehen oder einen Verifikationsstatus setzen.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-22.01 | Workflow-Modell und Versionierung | `todo` | P1 | M6 |
| F-22.02 | Visueller Workflow-Editor | `todo` | P2 | M6 |
| F-22.03 | Validierung von Workflows | `todo` | P1 | M6 |
| F-22.04 | Reproduzierbare Ausführung | `todo` | P1 | M6 |
| F-22.05 | Vergleich gegen Golden Tests | `todo` | P1 | M6 |
| F-22.06 | Dynamische Strategieregeln und adaptive Budgetsteuerung | `todo` | P2 | M6 |
| F-22.07 | Nachvollziehbare Budget- und Strategieentscheidungen | `todo` | P1 | M6 |
| F-22.08 | Benchmarkautomatisierung | `todo` | P2 | M6 |

## Features

### F-22.01 Workflow-Modell und Versionierung

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-07.03, F-07.15, F-06.02
- Quelle: UI §13.5, §20 (Stufe 3)
- Bearbeiter: offen · Nachweise: offen

Deklaratives Schema für Startbedingungen, Modelle, Strategien, Agenten, Tools, Prüfschritte, Fehler-Workflows und Budgetlimits. Jede Änderung erzeugt eine neue unveränderliche Version.

- [ ] Die Workflows A bis E aus ARCH §7 lassen sich im Schema ausdrücken.

### F-22.02 Visueller Workflow-Editor

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-22.01, F-15.01
- Quelle: UI §13.5, §20 (Stufe 3, Workflow-Editor)
- Bearbeiter: offen · Nachweise: offen

Editor mit Knoten für Schritte und Kanten für Aufgabensteuerung, visuell vom Proof Graph unterschieden.

- [ ] Ein Workflow lässt sich visuell erstellen, speichern und als neue Version laden.

### F-22.03 Validierung von Workflows

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-22.01
- Quelle: UI §20 (Stufe 3, Kriterium 1)
- Bearbeiter: offen · Nachweise: offen

Statische Prüfung auf fehlende Prüfschritte, unerreichbare Knoten, Zyklen ohne Abbruch, fehlende Budgetlimits und unzulässige Toolrechte.

- [ ] Ein Workflow ohne Verifikationsschritt vor einem Erfolgszustand wird abgelehnt.

### F-22.04 Reproduzierbare Ausführung

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-22.03, F-00.03
- Quelle: UI §20 (Stufe 3, Kriterium 1)
- Bearbeiter: offen · Nachweise: offen

Ein Run speichert Workflow-Version, Environment-Fingerprint und Seeds, sodass er wiederholbar ist.

- [ ] Zwei Läufe derselben Version mit gleichem Seed erzeugen dieselbe Entscheidungsfolge, soweit die Modelle deterministisch konfiguriert sind.

### F-22.05 Vergleich gegen Golden Tests

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-22.04, F-11.03
- Quelle: UI §20 (Stufe 3, Kriterium 2)
- Bearbeiter: offen · Nachweise: offen

Änderungen an Workflows und Agentenprofilen werden automatisch gegen die Golden Suite verglichen, bevor sie freigegeben werden.

- [ ] Eine Workflow-Version ohne Golden-Vergleich kann nicht als Standard gesetzt werden.

### F-22.06 Dynamische Strategieregeln und adaptive Budgetsteuerung

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-22.01, F-08.04, F-12.12
- Quelle: UI §20 (Stufe 3); ARCH §8.2
- Bearbeiter: offen · Nachweise: offen

Regeln, die abhängig von Zwischenergebnissen Strategien wechseln und Budget umverteilen, etwa auf Basis von Value-Schätzungen oder Fehlerklassen.

- [ ] Jede Regelanwendung erzeugt ein Event mit Auslöser und Wirkung.

### F-22.07 Nachvollziehbare Budget- und Strategieentscheidungen

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-22.06, F-19.01
- Quelle: UI §20 (Stufe 3, Kriterium 3)
- Bearbeiter: offen · Nachweise: offen

Budgetentscheidungen und Strategieänderungen sind in Timeline und Inspector mit Begründung, Eingangsdaten und Regelversion sichtbar.

- [ ] Für jede Budgetänderung im Run ist die auslösende Regel oder Person erkennbar.

### F-22.08 Benchmarkautomatisierung

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-22.05, F-11.06
- Quelle: UI §20 (Stufe 3, Benchmarkautomatisierung)
- Bearbeiter: offen · Nachweise: offen

Zeitgesteuerte oder ereignisgesteuerte Benchmarkläufe für neue Workflow-, Modell- und Profilversionen mit Ergebnissen im Model and Benchmark Laboratory.

- [ ] Ein neues Modellprofil löst automatisch einen Golden-Lauf aus.
