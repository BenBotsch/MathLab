# E15 Research Shell und Designsystem

- Status: `todo` · Meilenstein: M1, Ausbau M2 und M5
- Quellen: ARCH §14.1, §17.1, §18.3; UI §1.2, §1.3, §2, §3, §13.1, §14, §15.3, §19, §21 (Epic UI-02)
- Abhängige Epics: E14

## Ziel

Eine stabile Arbeitsoberfläche mit globaler Navigation, fünf Zonen, Run-Header und einem Designsystem, das Agentenstatus, mathematischen Befund und formale Verifikation getrennt und barrierefrei darstellt.

## Abgrenzung

Inhalte der Zonen liegen in E16 bis E21. Die Client-Plattform ist in OD-01 offen.

## Invarianten

Agentenstatus, mathematischer Befund und formale Verifikation werden nie vermischt (UI §1.3). Farbe ist nie die einzige Information (UI §4.3, §14.2). Frontend-Zustände erfinden keine verifizierten Ergebnisse (UI §15.3). Live- und Replay-Modus sind deutlich unterscheidbar.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-15.01 | Client-Grundgerüst | `ready` | P0 | M1 |
| F-15.02 | Globale Navigation | `todo` | P0 | M1 |
| F-15.03 | Workspace-Layout und Panelverwaltung | `todo` | P0 | M1 |
| F-15.04 | Run-Auswahl und Run-Header | `todo` | P0 | M1 |
| F-15.05 | Statuskarten, Laufzeit und Budgets | `todo` | P0 | M1 |
| F-15.06 | Design Tokens, Hell- und Dunkelmodus | `todo` | P0 | M1 |
| F-15.07 | Responsives Layout | `todo` | P1 | M1 |
| F-15.08 | Adaptive Detailtiefe | `todo` | P1 | M2 |
| F-15.09 | Getrennte Frontend-Zustände | `todo` | P0 | M1 |
| F-15.10 | UX-Regeln, Suche und mathematische Notation | `todo` | P1 | M1 |
| F-15.11 | Research Overview | `todo` | P0 | M2 |
| F-15.12 | System Configuration | `todo` | P1 | M2 |
| F-15.13 | Desktop-Verteilung | `todo` | P2 | M5 |
| F-15.14 | Exportierbare Ansichten | `todo` | P2 | M5 |

## Features

### F-15.01 Client-Grundgerüst

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.01 (OD-01), F-00.02
- Quelle: UI §19, §19.1, §19.2; ARCH §17.1, §18.3 (`apps/web`, `apps/desktop`)
- Bearbeiter: offen · Nachweise: offen

Lauffähiger Client mit Build, Tests, gepinnten Bibliotheksversionen und Anbindung an die API. UI §19.1 empfiehlt zuerst React mit TypeScript, ARCH §17.1 nennt Flutter-Desktop mit optionaler React-Web-UI. Die Entscheidung fällt in OD-01.

- [x] OD-01 ist als ADR entschieden ([ADR-0001](../../decisions/adr-0001-client-plattform.md)).
- [ ] Alle UI-Bibliotheken sind auf exakte Versionen gepinnt.
- [ ] Der Client lädt die Run-Liste aus `GET /runs`.

### F-15.02 Globale Navigation

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.01
- Quelle: UI §2.2
- Bearbeiter: offen · Nachweise: offen

Stabile linke Navigation mit den Gruppen Research (Overview, Active Runs, Problems, Proof Explorer), Knowledge (Theorems & Lemmas, Knowledge Graph, Methods), Laboratory (Experiments, Simulation, Models & Benchmarks) und System (Agents, Workflows, Settings). Innerhalb eines Runs wechseln Tabs oder Segmented Controls zwischen den Teilansichten. Noch nicht umgesetzte Seiten sind als solche erkennbar.

- [ ] Alle Einträge aus UI §2.2 sind vorhanden.

### F-15.03 Workspace-Layout und Panelverwaltung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.01
- Quelle: UI §3.1, §21 (Epic UI-02)
- Bearbeiter: offen · Nachweise: offen

Fünf Zonen: globale Navigation, Agent Explorer links, Research Canvas in der Mitte mit etwa 50 bis 60 Prozent der Breite, Detail Inspector rechts sowie Timeline und Console unten. Seitenpanels sind einklappbar, die Timeline ist in der Höhe veränderbar. Panelbreiten bleiben pro Benutzer erhalten.

- [ ] Alle fünf Zonen sind vorhanden und einklappbar oder größenveränderbar wie beschrieben.

### F-15.04 Run-Auswahl und Run-Header

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.03, F-14.02
- Quelle: UI §3.2, §21 (Epic UI-02)
- Bearbeiter: offen · Nachweise: offen

Header mit Problemname, Run-ID, Arbeitsmodus, natürlicher Zielaussage und aufklappbarer Formalisierung, Run-Status (Running, Paused, Completed, Failed, Cancelled), Budget und Restzeit, Zählern für aktive Agenten, Suchversuche, verifizierte Lemmata und offene Ziele, den Steuerungen Pause, Resume, Stop, Export und Run vergleichen sowie der Anzeige Live oder Replay. Die Steuerungen lösen Kommandos aus E20 aus.

- [ ] Der Header zeigt alle Elemente aus UI §3.2.
- [ ] Der Status ändert sich erst nach Backendbestätigung.

### F-15.05 Statuskarten, Laufzeit und Budgets

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.04, F-09.05
- Quelle: UI §3.3, §12.1, §21 (Epic UI-02); ARCH §14.1 (Research Dashboard)
- Bearbeiter: offen · Nachweise: offen

Statuskarten für aktive Agenten, Suchversuche, verifizierte Lemmata, offene Teilziele und Run-Zustand sowie Laufzeit und Budgetverbrauch, live über den Stream aktualisiert.

- [ ] Die Werte stimmen mit der Projektion aus F-09.05 überein.
- [ ] Es gibt keine Prozentanzeige für den Beweisfortschritt (UI §12.2).

### F-15.06 Design Tokens, Hell- und Dunkelmodus

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.01
- Quelle: UI §14.1, §14.2, §4.3, §21 (Epic UI-02)
- Bearbeiter: offen · Nachweise: offen

Tokens Primary (Blau, aktiv und ausgewählt), Success (Grün, formal verifiziert), Warning (Gelb oder Orange, wartend), Danger (Rot, Fehlschlag und Widerlegung), Discovery (Violett, Vermutung) und Neutral (Grau, Archiv). Dazu Statuskomponenten mit Label und Icon für die Knotenstatus aus UI §4.3.

Die visuelle Richtung folgt UI §14.1. Die Oberfläche ist ein wissenschaftliches Desktop-Werkzeug mit reduziertem, professionellem Interface. Sie bietet Hell- und Dunkelmodus, eine große zentrale Arbeitsfläche, wenig dekorative Animation und eine konsistente Typografie.

- [ ] Beide Modi erfüllen WCAG-AA-Kontrast für Text und Statuselemente. Die Wahl von WCAG AA ist eine Ergänzung des Backlogs.
- [ ] Jeder Status ist ohne Farbe allein über Label und Icon unterscheidbar.
- [ ] Schriften, Schriftgrößen und Abstände kommen ausschließlich aus Tokens.
- [ ] Die zentrale Arbeitsfläche nimmt im Standardlayout den größten Teil des Fensters ein.

### F-15.07 Responsives Layout

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-15.03
- Quelle: UI §21 (Epic UI-02), §3.1
- Bearbeiter: offen · Nachweise: offen

Panels klappen bei kleineren Fenstern automatisch ein, der Canvas bleibt nutzbar.

- [ ] Das Layout ist bei 1280 Pixel Breite ohne horizontales Scrollen bedienbar.

### F-15.08 Adaptive Detailtiefe

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-15.03
- Quelle: UI §14.3, §1.2
- Bearbeiter: offen · Nachweise: offen

Drei Stufen Overview, Explore und Inspect. Zoom und Kontextwechsel ändern den Detaillierungsgrad, ohne Informationen zu entfernen.

- [ ] Ein Wechsel der Stufe erhält Auswahl und Filter.

### F-15.09 Getrennte Frontend-Zustände

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-15.01, F-14.03
- Quelle: UI §15.3
- Bearbeiter: offen · Nachweise: offen

Fünf getrennte Zustandsarten: Server State, Event Projection, View State, Interaction State und Replay State.

- [ ] Ein Test zeigt, dass kein Client-Zustand einen Verifikationsstatus setzen kann.
- [ ] Ein Neustart des Clients verliert keine abgeschlossenen Events (UI §20, Kriterium 4).

### F-15.10 UX-Regeln, Suche und mathematische Notation

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-15.03
- Quelle: UI §14.4, §19 (KaTeX oder MathJax)
- Bearbeiter: offen · Nachweise: offen

Die acht UX-Regeln aus UI §14.4: lesbare Notation über KaTeX, Suche und Filter immer verfügbar, Selektion bleibt beim Ansichtswechsel erhalten, dosierte Aktualisierungen ohne Dauerblinken, Bestätigung von Mehrfachaktionen mit Backendbestätigung, klare Trennung von Live und Replay, Fehlermeldungen und Voraussetzungen mit wenigen Klicks erreichbar und exportierbare Ansichten (F-15.14).

- [ ] Jede Regel hat einen UI-Test oder eine dokumentierte manuelle Prüfung.

### F-15.11 Research Overview

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-15.02, F-14.02
- Quelle: UI §2.1 (Research Overview, P0), §13.1
- Bearbeiter: offen · Nachweise: offen

Globale Liste aller Projekte und Probleme mit Status, Datum, Agentenaktivität, letzter Erkenntnis, Kosten, Benchmark und Handlungsempfehlung, dazu aktive Runs, Warnungen und Erfolgsmetriken. In M1 genügt die Run-Auswahl aus F-15.04.

- [ ] Alle Spalten aus UI §13.1 sind vorhanden und filterbar.

### F-15.12 System Configuration

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-15.02, F-07.15, F-24.03
- Quelle: UI §2.1 (System Configuration), §20 (Stufe 3, Agenten- und Modellkonfiguration)
- Bearbeiter: offen · Nachweise: offen

Verwaltung von Providern, Methoden, Prompts, Budgets und Berechtigungen. Jede Änderung erzeugt eine neue Version und ein Audit-Event. Secrets werden nie angezeigt.

- [ ] Eine geänderte Konfiguration gilt nur für neue Runs, laufende Runs behalten ihre Version.

### F-15.13 Desktop-Verteilung

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-15.01 (OD-01)
- Quelle: UI §19 (Desktop-Verteilung), §19.1; ARCH §3.2 (Portabilität), §17.1
- Bearbeiter: offen · Nachweise: offen

Paketierung für Windows und Linux über einen Desktop-Wrapper oder eine Flutter-Shell mit eingebetteten Webflächen.

- [ ] Installierbare Pakete für Windows und Linux starten und verbinden sich mit dem Backend.

### F-15.14 Exportierbare Ansichten

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-15.03
- Quelle: UI §14.4 (letzte Regel)
- Bearbeiter: offen · Nachweise: offen

Graphen, Plots und Tabellen lassen sich für Dokumentation und Publikationen als SVG, PNG oder CSV exportieren.

- [ ] Ein exportierter Proof Graph enthält Statuslabels und nicht nur Farben.
