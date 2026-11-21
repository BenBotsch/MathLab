# E25 Eigenständige Forschung und Forschungsbeiträge

- Status: `todo` · Meilenstein: M6
- Quellen: ARCH §1.1, §2, §3.3, §19 (Phase 6), §20, §22, §23
- Abhängige Epics: E05, E07, E10, E11, E12

## Ziel

Das System bearbeitet eigenständige Forschungsaufgaben wie neue Vermutungen, Lemma-Extraktion und Methodentransfer. Die fünf Forschungsbeiträge A bis E aus ARCH §20 werden als prüfbare Experimente durchgeführt.

## Abgrenzung

Die Grundlagen wie Failure Memory, Transfer Model, Meta Controller und Ablationen liegen in E10, E11 und E12. Diese Epic definiert die Forschungsexperimente, ihre Hypothesen und ihre Auswertung.

## Invarianten

Die Beiträge sind Hypothesen und keine nachgewiesenen Innovationen. Vor jeder Veröffentlichung ist eine Neuheitsprüfung gegen die aktuelle Literatur nötig (ARCH §20, letzter Absatz). Neue Vermutungen bleiben CONJECTURED oder NUMERICALLY_SUPPORTED, bis sie formal bewiesen oder widerlegt sind.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-25.01 | Neuheitsprüfung und Literaturpflege | `todo` | P1 | M6 |
| F-25.02 | Beitrag A Learning from Failed Proofs | `todo` | P1 | M6 |
| F-25.03 | Beitrag B Cross-Domain Mathematical Transfer | `todo` | P2 | M6 |
| F-25.04 | Beitrag C Adaptive Hybrid Proof Systems | `todo` | P1 | M6 |
| F-25.05 | Beitrag D Proof Diversity Optimization | `todo` | P2 | M6 |
| F-25.06 | Beitrag E Continual Mathematical Knowledge Acquisition | `todo` | P2 | M6 |
| F-25.07 | Workflows für Vermutungsforschung und Exploration | `todo` | P1 | M6 |
| F-25.08 | Automatische Lemma-Extraktion | `todo` | P1 | M6 |
| F-25.09 | Expertenreview | `todo` | P1 | M6 |
| F-25.10 | Publikationsfragen aus Ablationen | `todo` | P2 | M6 |

## Features

### F-25.01 Neuheitsprüfung und Literaturpflege

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-07.12
- Quelle: ARCH §2, §20 (letzter Absatz), §23
- Bearbeiter: offen · Nachweise: offen

Gepflegte Literaturliste zu den Themen aus ARCH §2 und §23 und ein dokumentiertes Verfahren für die Neuheitsprüfung jedes Beitrags vor Veröffentlichung.

- [ ] Für jeden Beitrag A bis E liegt eine Neuheitsprüfung mit Datum und Quellen vor.

### F-25.02 Beitrag A Learning from Failed Proofs

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-10.08, F-11.10, F-11.12
- Quelle: ARCH §20 A
- Bearbeiter: offen · Nachweise: offen

Hypothese: strukturierte negative Erfahrungen verbessern Suchqualität und Recheneffizienz gegenüber rein erfolgsorientierter Speicherung. Experiment mit und ohne Failure Memory bei identischen Modellen, Budgets und Testproblemen. Metriken Pass@k, Compute per Proof, wiederholte Sackgassen und Correct Recovery Rate.

- [ ] Ergebnisse mit Konfidenzintervallen und vollständigem Protokoll liegen vor.

### F-25.03 Beitrag B Cross-Domain Mathematical Transfer

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-10.12, F-11.08
- Quelle: ARCH §20 B
- Bearbeiter: offen · Nachweise: offen

Hypothese: strukturbasierter Graph-Retrieval-Transfer ermöglicht Erfolg auf unbekannten Problemfamilien. Training auf einem oder mehreren Bereichen, Evaluation auf einem zurückgehaltenen Fachgebiet. Metriken OOD Success, Premise Recall, Transfer Rate und negative Transferfälle.

- [ ] Das zurückgehaltene Fachgebiet ist vor dem Experiment fixiert und auf Leakage geprüft.

### F-25.04 Beitrag C Adaptive Hybrid Proof Systems

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-12.12, F-11.10
- Quelle: ARCH §20 C
- Bearbeiter: offen · Nachweise: offen

Hypothese: ein Meta Controller, der LLM, CAS, SMT und numerische Exploration auswählt, braucht weniger Budget als statische Pipelines. Vergleich von Einzelsystemen und fester Orchestrierung mit adaptiver Budgetzuteilung. Metriken Pass@Budget, Time-to-Proof, Solver-Kosten und Ressourcenverteilung.

- [ ] Alle Varianten laufen mit identischem Gesamtbudget.

### F-25.05 Beitrag D Proof Diversity Optimization

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-08.10, F-11.14
- Quelle: ARCH §20 D
- Bearbeiter: offen · Nachweise: offen

Hypothese: explizite Methodenvielfalt erhöht die Zahl wiederverwendbarer allgemeiner Hilfssätze. Vergleich von Standard-Pass@k mit diversitätsgesteuerter Suche. Metriken verschiedene dependency-strukturelle Beweise, Lemma-Reuse und Verständlichkeit.

- [ ] Diversität wird strukturell gemessen und nicht über Textunterschiede.

### F-25.06 Beitrag E Continual Mathematical Knowledge Acquisition

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-12.11, F-10.09
- Quelle: ARCH §20 E
- Bearbeiter: offen · Nachweise: offen

Hypothese: externe verifizierte Wissensstrukturen und kontrolliertes Continual Training verbessern die Leistung langfristig ohne starke Regression. Vergleich kontinuierlicher Problemsequenzen mit isolierten Episoden sowie Memory-only mit Fine-Tuning. Metriken Retention, Forward Transfer, Backward Transfer und Compute-Effizienz.

- [ ] Regressionen auf der Golden Suite werden pro Schritt berichtet.

### F-25.07 Workflows für Vermutungsforschung und Exploration

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-07.13, F-05.05, F-05.06, F-11.02
- Quelle: ARCH §1.1, §3.3 (`CONJECTURE_RESEARCH`, `MATHEMATICAL_EXPLORATION`), §19 (Phase 6, neue Vermutungen)
- Bearbeiter: offen · Nachweise: offen

Abläufe für die Betriebsmodi `CONJECTURE_RESEARCH` und `MATHEMATICAL_EXPLORATION`: Muster in Daten finden, Vermutungen formulieren, numerisch testen, Gegenbeispiele suchen und Beweisversuche starten.

- [ ] Eine erzeugte Vermutung durchläuft nachweisbar die Stufen CONJECTURED, NUMERICALLY_SUPPORTED und dann FORMALLY_VERIFIED, REFUTED oder UNRESOLVED.

### F-25.08 Automatische Lemma-Extraktion

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-10.03, F-09.06
- Quelle: ARCH §19 (Phase 6)
- Bearbeiter: offen · Nachweise: offen

Aus verifizierten Beweisen werden allgemeine Hilfssätze extrahiert, formal neu geprüft und mit Provenienz in den Wissensgraphen aufgenommen.

- [ ] Jedes extrahierte Lemma hat einen eigenen Verifikationsnachweis.

### F-25.09 Expertenreview

- Status: `todo` · Priorität: P1 · Meilenstein: M6
- Abhängigkeiten: F-13.04, F-20.11
- Quelle: ARCH §19 (Phase 6, Expertenreview)
- Bearbeiter: offen · Nachweise: offen

Verfahren, mit dem Fachleute Formalisierungen, Vermutungen und Erklärungen bewerten. Bewertungen werden als Artefakte mit Autor gespeichert.

- [ ] Review-Ergebnisse fließen in die Bewertung der Erklärungsqualität aus F-13.11 ein.

### F-25.10 Publikationsfragen aus Ablationen

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-11.11, F-25.01
- Quelle: ARCH §19 (Phase 6)
- Bearbeiter: offen · Nachweise: offen

Aus quantitativen Ablationen werden neue Forschungsfragen abgeleitet und als Hypothese mit Experimentplan dokumentiert.

- [ ] Jede Frage verweist auf die Ablationsdaten, aus denen sie stammt.
