# E21 Knowledge and Experiment Laboratory UI

- Status: `todo` · Meilenstein: M2, Ausbau M3 bis M5
- Quellen: ARCH §14.1, §14.2, §19 (Phase 5); UI §2.1, §2.2, §6, §11, §12, §13.1 bis §13.4, §20 (Stufe 2), §21 (Epic UI-08)
- Abhängige Epics: E05, E10, E11, E12, E13, E15

## Ziel

Die Seiten für Wissen, Experimente, Beweisvergleich, Modelle, Benchmarks, Metriken und Reports machen die Forschungsergebnisse über einzelne Runs hinaus nutzbar.

## Abgrenzung

Die Daten liefern E05, E10, E11, E12 und E13. Diese Epic betrifft nur die Darstellung und Bedienung.

## Invarianten

Formale Beziehungen und semantische Ähnlichkeiten sind getrennt, vermutete Analogien sind als nicht verifiziert markiert (UI §6.2). Verifizierte und nur symbolisch berechnete Resultate sind unterschieden (UI §11.1). Es gibt keine Anzeige wie „Beweis zu 85 % fertig“ (UI §12.2).

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-21.01 | Ansicht des Wissensgraphen | `todo` | P1 | M2 |
| F-21.02 | Interaktionen im Wissensgraphen | `todo` | P1 | M3 |
| F-21.03 | Symbolic Workspace | `todo` | P1 | M2 |
| F-21.04 | Simulation Workspace | `todo` | P1 | M2 |
| F-21.05 | Proof Explorer | `todo` | P0 | M2 |
| F-21.06 | Model and Benchmark Laboratory | `todo` | P1 | M4 |
| F-21.07 | Metrik-Dashboards | `todo` | P1 | M2 |
| F-21.08 | Seite Research Reports | `todo` | P1 | M5 |
| F-21.09 | Problem Explorer | `todo` | P1 | M2 |
| F-21.10 | Parameterstudien und Gegenbeispiele | `todo` | P1 | M5 |
| F-21.11 | Seiten Theorems & Lemmas und Methods | `todo` | P1 | M3 |

## Features

### F-21.01 Ansicht des Wissensgraphen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-10.01, F-10.02, F-15.02
- Quelle: UI §6, §6.1, §6.2, §19 (Cytoscape.js), §20 (Stufe 2, Kriterium 1), §21 (Epic UI-08)
- Bearbeiter: offen · Nachweise: offen

Netzwerkansicht der Knotentypen aus UI §6.1 und der Beziehungstypen aus UI §6.2. In M2 genügt der einfache Graph aus verifizierten Lemmata und Fehlversuchen, die vollständige Struktur folgt mit M3.

- [ ] Ein verifiziertes Lemma ist zwischen Proof Graph und Wissensgraph in beide Richtungen auffindbar.
- [ ] Kanten mit Vertrauensebene unter verifiziert sind gestrichelt und beschriftet.

### F-21.02 Interaktionen im Wissensgraphen

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-21.01, F-10.09, F-10.11
- Quelle: UI §6.3
- Bearbeiter: offen · Nachweise: offen

Vom Beweisknoten zum Lemma springen, verwendete und mögliche Premises hervorheben, Abhängigkeitskette bis zu Definitionen und Axiomen verfolgen, Wiederverwendung über Probleme zeigen, alternative Herleitungen und Verallgemeinerungen zeigen, neue unverifizierte Beziehungen als Hypothesen markieren und nach Fachgebiet, Herkunft, Verifikation und Zeitraum filtern.

- [ ] Alle sieben Interaktionen aus UI §6.3 sind vorhanden.

### F-21.03 Symbolic Workspace

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-05.02, F-15.10
- Quelle: UI §11.1, §21 (Epic UI-08, symbolische Umformungsanzeige)
- Bearbeiter: offen · Nachweise: offen

Ausdrücke in LaTeX, schrittweise Umformungen als Pipeline mit Zwischenergebnissen, Transformationsquelle (SymPy, SageMath, Lean oder eigener Algorithmus), sichtbare Variablentypen, Voraussetzungen und Definitionsbereiche.

- [ ] Jeder Schritt zeigt Quelle und Vertrauensstatus, symbolisch und formal geprüft sind unterscheidbar.

### F-21.04 Simulation Workspace

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-05.04, F-15.10
- Quelle: UI §11.2, §11.3, §19 (Plotly), §20 (Stufe 2, Kriterium 3), §21 (Epic UI-08, Live-Simulationsplots)
- Bearbeiter: offen · Nachweise: offen

Live-Plots mit wählbaren Parametern, Zeitreihen, Parameterflächen, Nullstellen, Diskontinuitäten und Extremwerte, Vergleich mehrerer Läufe und Seeds, Anzeige von Präzision, Toleranzen, Bedingungen und Modellversion. Referenzszenario ist f(x, α) = x³ − αx + 1 mit Nullstellen, kritischen Parametern und Vermutungen.

- [ ] Die Simulation zeigt Parameter, Modell, Seed, Präzision und Ergebnisstatus.
- [ ] Im Referenzszenario haben Symbolik und formale Prüfung getrennte Events und Vertrauensstatus.

### F-21.05 Proof Explorer

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-16.08, F-11.14
- Quelle: UI §2.1 (Proof Explorer, P0), §13.2; ARCH §14.1 (Proof Tree)
- Bearbeiter: offen · Nachweise: offen

Fertige und partielle Beweise mit Varianten und Prüfstatus. Vergleich formal geprüfter Beweise desselben Theorems nach Hilfssätzen, Methoden, Länge, Laufzeit, Verständlichkeit und Wiederverwendbarkeit.

- [ ] Zwei unterschiedliche Beweise desselben Zielstatements sind vergleichbar (UI §20, Stufe 2).

### F-21.06 Model and Benchmark Laboratory

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-11.03, F-11.11, F-12.13
- Quelle: UI §2.1, §13.3; ARCH §14.1 (Model Lab)
- Bearbeiter: offen · Nachweise: offen

Vergleich von Modellversionen, Prompt- und Strategievarianten, Golden Tasks, Ablationen, Trainingsläufen und Ressourcen mit reproduzierbaren A/B-Experimenten. Eine einfache Ergebnistabelle der Golden Suite reicht ab M1 über die CLI (F-14.09).

- [ ] A/B-Vergleiche zeigen Budget, Seeds und Konfidenzintervalle aus F-11.12.

### F-21.07 Metrik-Dashboards

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-09.05, F-11.09
- Quelle: UI §12.1, §12.2; ARCH §14.1 (Research Dashboard)
- Bearbeiter: offen · Nachweise: offen

Run-Kennzahlen aus UI §12.1 und wissenschaftliche Qualitätsmetriken aus UI §12.2 mit den dort genannten Visualisierungen und Bemerkungen, etwa Pass@k nur bei gleichem Budget und Value Estimate mit Unsicherheit.

- [ ] Formal Success ist ein eindeutiger Status ohne Prozentwert.
- [ ] Geschätzte Lösbarkeit und Value Estimate sind als Schätzung gekennzeichnet.

### F-21.08 Seite Research Reports

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-13.04, F-13.05
- Quelle: UI §2.1, §13.4, §21 (Epic UI-08, Reports und Exportformate)
- Bearbeiter: offen · Nachweise: offen

Liste versionierter Reports mit Vorschau und Export in Markdown, LaTeX, PDF und Lean.

- [ ] Ein Report enthält alle acht Bestandteile aus UI §13.4.

### F-21.09 Problem Explorer

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-03.01, F-03.06, F-15.02
- Quelle: ARCH §14.1 (Problem Explorer); UI §2.2 (Problems)
- Bearbeiter: offen · Nachweise: offen

Liste und Detail aller Probleme mit Originaltext, formaler Zielaussage, Hash, Klassifikation, Varianten und zugehörigen Runs. Neue Probleme werden hier importiert.

- [ ] Original und formale Aussage sind nebeneinander sichtbar, die Originalaussage ist nicht editierbar.

### F-21.10 Parameterstudien und Gegenbeispiele

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-21.04, F-05.05, F-05.07
- Quelle: UI §2.1 (Experiment Laboratory), §11.2; ARCH §19 (Phase 5)
- Bearbeiter: offen · Nachweise: offen

Übersicht von Parameterstudien und gefundenen Gegenbeispielen mit Markierung, Export und Link zur widerlegten Hypothese.

- [ ] Ein Gegenbeispiel lässt sich exportieren und mit seinen Bedingungen reproduzieren.

### F-21.11 Seiten Theorems & Lemmas und Methods

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-10.05, F-06.05, F-15.02
- Quelle: UI §2.2 (Knowledge)
- Bearbeiter: offen · Nachweise: offen

Durchsuchbare Listen der Theoreme und Lemmata mit Vertrauensebene und Provenienz sowie der Beweismethoden mit Erfahrungsstatistik.

- [ ] Jedes Lemma zeigt Verifikationsstatus und Quelle.
