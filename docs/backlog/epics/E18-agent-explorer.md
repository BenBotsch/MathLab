# E18 Agent Explorer und Agent Execution Graph

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §6.2, §14.1 (Agent Monitor); UI §2.1 (Agent Explorer), §3.1, §5, §12.1, §17.1, §20 (Stufe 1 und 2), §21 (Epic UI-05)
- Abhängige Epics: E07, E14, E15, E23

## Ziel

Die operative Ausführung der Agenten wird sichtbar: wer arbeitet woran, mit welchem Modell, welchen Werkzeugen, welchen Kosten und mit welchem mathematischen Auftrag.

## Abgrenzung

Der Agent Execution Graph zeigt die operative Ausführung, nicht die Beweislogik (E16). Die Detailansicht eines Agenten liegt in F-17.09. Steuerkommandos werden in E20 definiert und hier nur ausgelöst.

## Invarianten

Eine mathematische Abhängigkeit wird nie allein daraus abgeleitet, dass zwei Agenten Nachrichten austauschen (UI §5.1). Agentenaktionen nutzen die getrennte Control API und werden protokolliert (UI §5.3). Änderungen an Strategie, Modell oder Budget gelten nur für einen neuen Versuch.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-18.01 | Agentenliste mit Hierarchie und Status | `todo` | P0 | M1 |
| F-18.02 | Agentenkarte | `todo` | P0 | M1 |
| F-18.03 | Agent Execution Graph | `todo` | P1 | M1 |
| F-18.04 | Toolaufrufe, Latenzen und Kosten | `todo` | P1 | M1 |
| F-18.05 | Technischen Trace mit mathematischem Task verbinden | `todo` | P1 | M2 |
| F-18.06 | Agentenaktionen | `todo` | P1 | M2 |
| F-18.07 | Seite Agent Explorer mit Warteschlangen | `todo` | P1 | M2 |
| F-18.08 | Agentenvergleich | `todo` | P2 | M2 |

## Features

### F-18.01 Agentenliste mit Hierarchie und Status

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.03, F-14.03, F-07.03
- Quelle: UI §3.1 (Agent Explorer links), §20 (Stufe 1, Agentenliste), §21 (Epic UI-05, Hierarchie und Agentenstatus)
- Bearbeiter: offen · Nachweise: offen

Linkes Panel mit allen Agenten eines Runs in ihrer Auftragshierarchie, Laufstatus und aktueller Aufgabe, live aus dem Eventstrom. Viele Agenten werden über eine virtuelle Liste dargestellt (UI §18.1).

- [ ] `agent.started` macht den Agenten ohne Neuladen aktiv sichtbar.
- [ ] Ein abgestürzter Agent zeigt Fehlerstatus und letzte bekannte Aktivität (UI §18.2).

### F-18.02 Agentenkarte

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-18.01, F-07.01
- Quelle: UI §5.2
- Bearbeiter: offen · Nachweise: offen

Karte mit Agenten-ID und Rolle, Task-ID und mathematischem Ziel, Modellname, Version und Inferenzkonfiguration, Laufstatus und Startzeit, Tokenverbrauch, Dauer und Ressourcen, letztem Toolaufruf, Zahl erzeugter und formal verifizierter Teilziele sowie Arbeitsphase und offenen Toolergebnissen.

- [ ] Alle acht Angaben aus UI §5.2 sind vorhanden.
- [ ] Erzeugte und verifizierte Teilziele werden getrennt gezählt.

### F-18.03 Agent Execution Graph

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-18.01, F-14.02
- Quelle: UI §5, §5.1
- Bearbeiter: offen · Nachweise: offen

Graph aus `GET /runs/{id}/agent-graph`. Kanten zeigen Auftrag, Ergebnis, Datenfluss und Abhängigkeit. Die Darstellung ist visuell klar vom Proof Graph unterschieden.

- [ ] Kantentypen sind beschriftet, keine Kante heißt `DEPENDS_ON` im mathematischen Sinn.

### F-18.04 Toolaufrufe, Latenzen und Kosten

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-18.02, F-23.05
- Quelle: UI §12.1, §21 (Epic UI-05, Toolaufrufe, Modellnamen, Latenzen und Kosten)
- Bearbeiter: offen · Nachweise: offen

Liste der Toolaufrufe pro Agent mit Modell, Latenz, Kosten, Ergebnisstatus und Retries.

- [ ] Summen pro Agent stimmen mit den Run-Kennzahlen aus F-09.05 überein.

### F-18.05 Technischen Trace mit mathematischem Task verbinden

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-18.04, F-23.04
- Quelle: UI §17.1, §21 (Epic UI-05)
- Bearbeiter: offen · Nachweise: offen

Von einem Toolaufruf oder Span gelangt man zum zugehörigen Proof-Knoten, ProofAttempt oder Experiment und zurück.

- [ ] Jeder Span mit `proof_node_id` öffnet den Knoten im Inspector.

### F-18.06 Agentenaktionen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-18.02, F-20.06, F-20.05, F-20.01
- Quelle: UI §5.3, §21 (Epic UI-05, Agentenaufträge kontrolliert verwalten)
- Bearbeiter: offen · Nachweise: offen

Aus der Karte heraus Details und eigene Timeline öffnen, Auftrag pausieren oder kontrolliert abbrechen, Folgetask erstellen, Strategie, Modell oder Budget für einen neuen Versuch ändern, Hinweis übergeben und fehlgeschlagene Aktionen mit geändertem Kontext erneut ausführen.

- [ ] Jede Aktion erzeugt ein Kommando über F-14.04 und ein Audit-Event.
- [ ] Eine erneute Ausführung erzeugt einen neuen Versuch, der alte bleibt unverändert.

### F-18.07 Seite Agent Explorer mit Warteschlangen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-18.01, F-15.02
- Quelle: UI §2.1 (Agent Explorer, P0), §2.2 (System, Agents); ARCH §14.1 (Agent Monitor, Warteschlangen)
- Bearbeiter: offen · Nachweise: offen

Eigene Seite über Runs hinweg mit Hierarchie, Aufträgen, Modellen, Tools und Warteschlangen. In M1 genügt das Panel aus F-18.01.

- [ ] Warteschlangen zeigen wartende Aufträge mit Wartezeit.

### F-18.08 Agentenvergleich

- Status: `todo` · Priorität: P2 · Meilenstein: M2
- Abhängigkeiten: F-18.04
- Quelle: UI §20 (Stufe 2, Agentenvergleiche)
- Bearbeiter: offen · Nachweise: offen

Vergleich von Agenten oder Agentenprofilen nach Erfolg, Kosten und Fehlerklassen bei gleichem Budget.

- [ ] Vergleiche mit ungleichem Budget werden als nicht vergleichbar markiert.
