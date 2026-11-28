# E19 Timeline, Console und Replay

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §14.1 (Experiment Explorer); UI §3.1, §8, §9, §10.1 (Fork / Re-Run), §17.2, §18.2, §20 (Stufe 1), §21 (Epic UI-06)
- Abhängige Epics: E02, E14, E15, E16

## Ziel

Alle Ereignisse eines Runs sind live und historisch nachvollziehbar. Ein Zeitregler rekonstruiert jeden früheren Zustand, und von dort lässt sich ein neuer Run ableiten.

## Abgrenzung

Event Store, Sequenzen und Snapshots liegen in E02. Diese Epic betrifft Darstellung, Filter, Replay-Bedienung und den Fork-Ablauf.

## Invarianten

Historische Zustände sind schreibgeschützt (UI §9.3, §18.2). Direkte historische Datenmutation ist nicht erlaubt. `Fork from Here` erzeugt einen neuen Run mit Provenienz und überschreibt nichts. Replay erzeugt aus Snapshot und Eventfolge denselben UI-Zustand (UI §20, Kriterium 5).

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-19.01 | Live-Timeline | `todo` | P0 | M1 |
| F-19.02 | Timeline-Filter und Suche | `todo` | P0 | M1 |
| F-19.03 | Timeline-Ansichten und Swimlanes | `todo` | P1 | M2 |
| F-19.04 | Ansichtsübergreifende Hervorhebung | `todo` | P1 | M1 |
| F-19.05 | Console | `todo` | P1 | M1 |
| F-19.06 | Zeitregler und Snapshot-Rekonstruktion | `todo` | P0 | M1 |
| F-19.07 | Schreibgeschützter Replay-Modus | `todo` | P0 | M1 |
| F-19.08 | Fork from Here | `todo` | P1 | M2 |
| F-19.09 | Deterministische Replay-Tests | `todo` | P0 | M1 |
| F-19.10 | Experiment Explorer | `ready` | P1 | M2 |

## Features

### F-19.01 Live-Timeline

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.03, F-15.03
- Quelle: UI §3.1 (Timeline unten), §8.1, §20 (Stufe 1, Kriterium 1)
- Bearbeiter: offen · Nachweise: offen

Chronologische Timeline aller Events eines Runs mit Typ, Zeit, Agent, Severity und Kurztext, über eine virtuelle Liste. Die Events aus der Tabelle in UI §8.1 haben eine definierte Darstellung.

- [ ] Ein Agentenevent erscheint während der Ausführung in der Timeline.
- [ ] Alle 15 Eventtypen aus UI §8.1 haben eine Darstellung und einen UI-Test.

### F-19.02 Timeline-Filter und Suche

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-19.01
- Quelle: UI §8.3, §21 (Epic UI-06, Eventfilter und Suche)
- Bearbeiter: offen · Nachweise: offen

Filter nach Agent-ID, Eventtyp, Severity, Proof Node, Zeitraum, Verifikationsstatus, Methode, Modellversion und Fehlerklasse sowie Volltextsuche.

- [ ] Alle neun Filter aus UI §8.3 sind kombinierbar.

### F-19.03 Timeline-Ansichten und Swimlanes

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-19.01
- Quelle: UI §8.2, §21 (Epic UI-06, Swimlanes nach Agent, Tool und Branch)
- Bearbeiter: offen · Nachweise: offen

Ansichten chronologisch, nach Agent als Swimlanes, nach Suchzweig, nach Verifikation und nach Tool (Lean, CAS, SMT, Simulation, Datenbank).

- [ ] Jede der fünf Ansichten zeigt dieselben Events wie die chronologische Ansicht mit passendem Filter.

### F-19.04 Ansichtsübergreifende Hervorhebung

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-19.01, F-16.06
- Quelle: UI §8.3 (letzter Absatz)
- Bearbeiter: offen · Nachweise: offen

Ein Klick auf ein Event hebt den zugehörigen Knoten in allen geöffneten Ansichten hervor.

- [ ] Klick auf `proof.step.rejected` markiert den Knoten im Proof Graph und öffnet den Fehler im Inspector.

### F-19.05 Console

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-19.01, F-14.06
- Quelle: UI §3.1 (Timeline und Console)
- Bearbeiter: offen · Nachweise: offen

Untere Zone mit technischen Logs und Toolausgaben, nachgeladen über Artefakt-IDs. Die Console ist eine reine Anzeige und führt keine Kommandos aus. Diese Abgrenzung ist eine Festlegung des Backlogs, Kommandos laufen über E20.

- [ ] Logs werden nur bei Bedarf geladen und virtuell dargestellt.

### F-19.06 Zeitregler und Snapshot-Rekonstruktion

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.06, F-19.01
- Quelle: UI §9.1, §9.2, §9.3, §21 (Epic UI-06)
- Bearbeiter: offen · Nachweise: offen

Slider, der einen gespeicherten Run zeitpunktweise rekonstruiert. Synchron rekonstruiert werden Agentenstatus und Aufträge, Beweisgraph und offene Teilziele, bekannte Hypothesen, frühere Fehler und Gegenbeispiele, Modell- und Toolversionen, Metriken und Ressourcen sowie ab M3 Wissensgraph-Änderungen.

- [ ] Der vollständige Replay eines Demo-Runs ist möglich (UI §20, Stufe 1).
- [ ] Die Beispielhistorie aus UI §9.1 lässt sich als Testfall nachstellen.

### F-19.07 Schreibgeschützter Replay-Modus

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-19.06, F-15.09
- Quelle: UI §9.3, §14.4, §18.2 (Replay)
- Bearbeiter: offen · Nachweise: offen

Im Replay sind alle mutierenden Aktionen deaktiviert. Der Modus ist im Run-Header und in jeder Zone deutlich als Replay erkennbar.

- [ ] Im Replay kann kein Kommando an die Control API gesendet werden (Test).

### F-19.08 Fork from Here

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-19.07, F-08.05, F-14.04
- Quelle: UI §9.3, §10.1 (Historischer Zustand), §21 (Epic UI-06)
- Bearbeiter: offen · Nachweise: offen

Aus einem historischen Zustand wird ein neuer Run mit Provenienz auf Sequenznummer und konkreter Konfiguration erzeugt. Auch ein Re-Run mit gleicher Konfiguration ist möglich.

- [ ] Der neue Run verweist auf Quell-Run und Sequenz, der Quell-Run bleibt unverändert.

### F-19.09 Deterministische Replay-Tests

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-19.06, F-02.06
- Quelle: UI §20 (Kriterium 5), §21 (Epic UI-06)
- Bearbeiter: offen · Nachweise: offen

Tests vergleichen den UI-Zustand aus Snapshot plus Eventfolge mit dem Live-Zustand am selben Sequenzpunkt.

- [ ] Für den Demo-Run sind beide Zustände an mehreren Sequenzpunkten identisch.

### F-19.10 Experiment Explorer

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-09.01, F-14.02
- Quelle: ARCH §14.1 (Experiment Explorer)
- Bearbeiter: offen · Nachweise: offen

Durchsuchbare Ansicht aller ProofAttempts und Experimente mit Prompt, Werkzeugen, Fehlern und Ergebnissen über Runs hinweg.

- [ ] Ein Versuch lässt sich über seine ID finden und mit allen Pflichtfeldern aus F-09.02 anzeigen.
