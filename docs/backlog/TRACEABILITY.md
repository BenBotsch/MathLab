# Traceability

Diese Matrix ordnet jeden Abschnitt und Unterabschnitt beider Quelldokumente den Features zu, die ihn umsetzen. Sie ist der Nachweis, dass nichts aus den Quellen verloren gegangen ist. Die Zuordnung folgt der Zeile `Quelle` in jedem Feature. Wer eine Quelle eines Features ändert, aktualisiert auch diese Tabelle.

- ARCH: [Forschungs- und Architekturkonzept](../research/Mathematisches_Beweissystem_Forschungs_und_Architekturkonzept.md)
- UI: [UI Research Control Center](../research/Mathematisches_Beweissystem_UI_Research_Control_Center.md)

Ein Abschnitt ohne Feature trägt einen Vermerk. „Referenz“ bedeutet Literatur ohne eigene Umsetzung. „Oberabschnitt“ bedeutet, dass die Unterabschnitte die Inhalte tragen.

## ARCH Forschungs- und Architekturkonzept

| Abschnitt | Titel | Features | Vermerk |
| --- | --- | --- | --- |
| §1 | Vision und Ziele | keine | Oberabschnitt, siehe Unterabschnitte |
| §1.1 | Die zentralen Fähigkeiten | F-10.09, F-25.07 | Übersicht der Fähigkeiten, im Einzelnen in §3.1 und den Fach-Epics |
| §1.2 | Zentrale Unterscheidung: Erkenntnisstufen | F-01.01 | Zusätzlich Glossar und Invariante in AGENTS.md |
| §2 | Wissenschaftliche Grundlagen und Forschungslage | F-25.01 | Forschungslage, Grundlage der Neuheitsprüfung |
| §2.1 | Formale Proof-Modelle und Suchverfahren | F-04.02, F-08.02, F-08.07, F-08.08, F-08.09, F-12.03 |  |
| §2.2 | Agentische mathematische Forschung | F-11.07 |  |
| §2.3 | Mathematische Wissensgraphen und Premise Retrieval | F-03.05, F-10.10, F-10.11 |  |
| §2.4 | Forschung zu Lernsignalen und Beweisqualität | F-11.05, F-11.13, F-11.14, F-12.06 |  |
| §3 | Anforderungen und Betriebsmodi | keine | Oberabschnitt, siehe Unterabschnitte |
| §3.1 | Funktionale Anforderungen | F-03.01, F-03.02, F-03.06, F-03.09, F-04.08, F-05.05, F-08.06, F-08.10, F-10.05 |  |
| §3.2 | Nichtfunktionale Anforderungen | F-00.03, F-00.04, F-00.08, F-01.05, F-15.13 |  |
| §3.3 | Betriebsmodi | F-01.06, F-08.10, F-11.02, F-25.07 |  |
| §4 | Gesamtarchitektur | keine | Oberabschnitt, siehe Unterabschnitte |
| §4.1 | Hauptkomponenten | F-06.02, F-07.03, F-11.14 |  |
| §4.2 | Architekturprinzipien | F-01.03, F-01.04, F-01.05, F-03.03 |  |
| §5 | Mathematische Methoden als ausführbare Strategien | keine | Oberabschnitt, siehe Unterabschnitte |
| §5.1 | Beweismethodenkatalog | F-06.04 |  |
| §5.2 | Methoden als versionierte Objekte | F-06.01, F-06.02, F-06.05, F-06.06 |  |
| §6 | KI-Modelle und Multiagentensystem | keine | Oberabschnitt, siehe Unterabschnitte |
| §6.1 | Modellrollen | F-03.06, F-06.06, F-07.04, F-07.06, F-07.10, F-07.11, F-07.13, F-08.04, F-10.06, F-10.12, F-12.02, F-12.03, F-12.12, F-13.02 |  |
| §6.2 | Agentenrollen | F-07.07, F-07.08, F-07.09, F-07.10, F-07.11, F-07.12, F-08.04, F-13.02 |  |
| §6.3 | Typisierte Agentenkommunikation | F-01.07, F-07.02 |  |
| §6.4 | Agentenkoordination und Isolation | F-07.03, F-07.05, F-07.10, F-11.02, F-24.01, F-24.02 |  |
| §7 | End-to-End-Workflows | keine | Oberabschnitt, siehe Unterabschnitte |
| §7.1 | Workflow A – Problemaufnahme | F-03.01, F-03.02, F-03.03, F-03.04, F-03.05, F-03.06, F-03.09 |  |
| §7.2 | Workflow B – Strategische Exploration | F-04.08, F-06.06, F-07.03, F-07.04, F-07.07, F-07.11, F-08.06, F-08.07, F-08.08, F-10.03 |  |
| §7.3 | Workflow C – Verifikation | F-04.01, F-04.03, F-04.04, F-04.05, F-04.06, F-04.07, F-07.09 |  |
| §7.4 | Workflow D – Nachbearbeitung und Lernen | F-08.10, F-09.04, F-09.06, F-10.03, F-11.14, F-12.08, F-13.04 |  |
| §7.5 | Workflow E – Widerlegungen | F-05.03, F-05.06, F-05.07, F-07.13 |  |
| §8 | Proof Search und Suchsteuerung | F-08.01, F-08.02 |  |
| §8.1 | Algorithmischer Vergleich | F-08.02, F-08.03, F-08.08, F-08.09, F-08.11 |  |
| §8.2 | Search Budget Controller | F-08.04, F-08.05, F-08.08, F-22.06 |  |
| §9 | Trial-and-Error, Experimentdaten und Feedback | keine | Oberabschnitt, siehe Unterabschnitte |
| §9.1 | ProofAttempt-Datenmodell | F-09.01, F-09.07 |  |
| §9.2 | Weitere zu protokollierende Felder | F-00.03, F-01.05, F-07.15, F-09.02, F-23.05 |  |
| §9.3 | Fehlerkatalog | F-08.07, F-09.03, F-09.04, F-10.08 |  |
| §9.4 | Eventtypen | F-02.02, F-02.03, F-02.05, F-02.10 |  |
| §10 | Metriken, Reward und Lernverfahren | keine | Oberabschnitt, siehe Unterabschnitte |
| §10.1 | Harte und weiche Metriken getrennt halten | F-09.05, F-09.07, F-09.08, F-11.09, F-11.14, F-12.01, F-13.11 |  |
| §10.2 | Value-Modell | F-12.03 |  |
| §10.3 | Reward-Vorschlag | F-12.04, F-12.05 |  |
| §10.4 | Vier Lernstufen | F-12.06, F-12.07, F-12.09, F-12.11, F-12.13 |  |
| §11 | Wissensgraph und mathematisches Langzeitgedächtnis | keine | Oberabschnitt, siehe Unterabschnitte |
| §11.1 | Objektklassen | F-10.01 |  |
| §11.2 | Typisierte Relationen | F-10.02, F-10.04, F-10.11 |  |
| §11.3 | Hybrides Retrieval | F-10.05, F-10.06, F-10.10 |  |
| §11.4 | Mathematische Normalisierung und Fingerprints | F-03.07, F-10.05, F-10.11 |  |
| §11.5 | Positive und negative Memory | F-09.04, F-10.07, F-10.08 |  |
| §12 | Symbolische Berechnung, Simulation und Gegenbeispiele | keine | Oberabschnitt, siehe Unterabschnitte |
| §12.1 | Werkzeuglandschaft | F-05.01, F-05.02, F-05.03, F-05.04, F-05.08, F-05.09 |  |
| §12.2 | Simulationsworkflow | F-05.04, F-05.05 |  |
| §12.3 | Counterexample-Guided Reasoning | F-05.03, F-05.06, F-05.07 |  |
| §13 | Formale Beweise und Vertrauensgrenzen | keine | Oberabschnitt, siehe Unterabschnitte |
| §13.1 | Lean als Trusted Checker | F-04.04 |  |
| §13.2 | Maßnahmen | F-01.03, F-03.05, F-04.04, F-04.05, F-04.06, F-04.10, F-05.02 |  |
| §14 | Erklärung, Visualisierung und Benutzeroberfläche | keine | Oberabschnitt, siehe Unterabschnitte |
| §14.1 | Hauptansichten | F-13.10, F-15.05, F-18.07, F-19.10, F-21.05, F-21.06, F-21.07, F-21.09 |  |
| §14.2 | Visualisierungstechnologien | F-13.07, F-13.08, F-13.09 |  |
| §14.3 | Erklärungskette | F-13.01, F-13.02, F-13.03, F-13.06, F-13.07, F-17.10 |  |
| §15 | Beispiel: Summe ungerader Zahlen | F-08.10, F-11.04 |  |
| §15.1 | Experimentelle Beobachtung | F-05.04, F-11.04 | Beispiel, Teil des Referenzbeispiels F-11.04 |
| §15.2 | Algebraischer Beweis | F-08.10, F-11.04 | Beispiel, Teil des Referenzbeispiels F-11.04 |
| §15.3 | Induktiver Beweis | F-08.10, F-11.04 | Beispiel, Teil des Referenzbeispiels F-11.04 |
| §15.4 | Geometrischer Beweis | F-07.14, F-13.07 |  |
| §15.5 | Systemworkflow | F-07.07, F-07.14, F-11.14 |  |
| §16 | Benchmarks und wissenschaftliche Evaluation | keine | Oberabschnitt, siehe Unterabschnitte |
| §16.1 | Wichtige Datensätze | F-03.04, F-11.06, F-11.07, F-11.13 |  |
| §16.2 | Golden-Test-Suite | F-11.01, F-11.03, F-11.05, F-11.13 |  |
| §16.3 | Metriken und Vergleichbarkeit | F-11.09, F-13.11 |  |
| §16.4 | Datenkontamination und Reproduzierbarkeit | F-03.08, F-11.02, F-11.08, F-11.10, F-11.11, F-11.12 |  |
| §17 | Technologie- und Infrastrukturentscheidungen | keine | Oberabschnitt, siehe Unterabschnitte |
| §17.1 | Konkrete Empfehlungen | F-00.01, F-00.04, F-00.05, F-02.07, F-04.01, F-04.02, F-05.01, F-05.08, F-07.01, F-10.06, F-12.13, F-15.01, F-15.13, F-23.02, F-23.03 | Plattformwahl offen in OD-01, Lean-Interaktion in OD-02, Modelle in OD-03 |
| §17.2 | Speicherarchitektur | F-02.03, F-02.07, F-10.01 |  |
| §17.3 | Lokale Hardware und Kosten | F-00.01, F-00.07, F-07.01, F-12.10, F-23.05 | Lokale Modelle offen in OD-03 |
| §18 | Datenmodelle, Schnittstellen und Projektstruktur | keine | Oberabschnitt, siehe Unterabschnitte |
| §18.1 | Kernentitäten | F-01.02, F-03.08, F-05.07 |  |
| §18.2 | Schnittstellenbeispiele | F-01.04, F-14.01, F-23.01 |  |
| §18.3 | Projektstruktur | F-00.01, F-00.02, F-14.09, F-15.01 |  |
| §18.4 | Persistenz, Idempotenz und Konsistenz | F-01.03, F-02.04, F-04.04, F-04.09, F-10.02, F-10.03 |  |
| §19 | Entwicklungsroadmap und Akzeptanzkriterien | F-06.03, F-07.04, F-07.12, F-08.05, F-10.06, F-10.08, F-10.09, F-10.12, F-11.01, F-11.04, F-11.10, F-11.13, F-12.02, F-12.05, F-12.06, F-12.07, F-12.09, F-12.11, F-12.13, F-13.03, F-13.04, F-13.05, F-14.09, F-21.10, F-25.07, F-25.08, F-25.09, F-25.10 | Phasen, siehe Unterzeilen und ROADMAP.md |
| §19 Phase 1 | Proof Engine MVP (grob 4–6 Wochen) | F-07.04, F-11.01, F-11.04, F-14.09 |  |
| §19 Phase 2 | Mehrere Agenten und Beweismethoden (weitere 4–8 Wochen) | F-06.03, F-08.05, F-11.10 |  |
| §19 Phase 3 | Wissensgraph und Langzeitgedächtnis (weitere 6–10 Wochen) | F-10.06, F-10.08, F-10.09 |  |
| §19 Phase 4 | ML/RL | F-12.02, F-12.05, F-12.06, F-12.07, F-12.09, F-12.11, F-12.13 |  |
| §19 Phase 5 | Dashboard, Simulation, Erklärungen | F-13.03, F-13.04, F-13.05, F-21.10 |  |
| §19 Phase 6 | Eigenständige Forschungsaufgaben | F-07.12, F-10.12, F-11.13, F-25.07, F-25.08, F-25.09, F-25.10 |  |
| §20 | Mögliche eigenständige Forschungsbeiträge | F-10.12, F-12.11, F-12.12, F-25.01, F-25.02, F-25.03, F-25.04, F-25.05, F-25.06 |  |
| §20 A | Learning from Failed Proofs | F-25.02 |  |
| §20 B | Cross-Domain Mathematical Transfer | F-25.03 |  |
| §20 C | Adaptive Hybrid Proof Systems | F-25.04 |  |
| §20 D | Proof Diversity Optimization | F-25.05 |  |
| §20 E | Continual Mathematical Knowledge Acquisition | F-25.06 |  |
| §21 | Risiken, Sicherheitsregeln und Qualitätssicherung | F-00.03, F-00.07, F-01.01, F-03.05, F-04.03, F-04.05, F-10.04, F-11.08, F-20.11, F-24.01, F-24.05, F-24.06, F-24.09 | Vollständiges Register in F-24.09 |
| §21.1 | Qualitäts-Gates in CI | F-00.05, F-00.06, F-11.03, F-24.08 |  |
| §22 | Priorisierte Umsetzungsempfehlung | F-04.01, F-06.03, F-07.01, F-07.04, F-10.01, F-10.03, F-11.01, F-11.03, F-11.10 | Reihenfolge der Roadmap, siehe ROADMAP.md |
| §23 | Literatur und weiterführende Ressourcen | F-25.01 | Referenz, gepflegt in F-25.01 |
| §23.1 | Formales Beweisen und Mathematikbibliotheken | keine | Referenz |
| §23.2 | Kern-Paper zu Beweismodellen | keine | Referenz |
| §23.3 | Agenten, Forschung und Langzeitgedächtnis | keine | Referenz |
| §23.4 | Retrieval, Beweisqualität und Evaluation | keine | Referenz |
| §23.5 | Daten- und MLOps-Werkzeuge | keine | Referenz |

## UI Research Control Center

| Abschnitt | Titel | Features | Vermerk |
| --- | --- | --- | --- |
| §1 | Vision und Leitprinzipien | keine | Oberabschnitt, siehe Unterabschnitte |
| §1.1 | Kernfragen der Benutzeroberfläche | keine | Leitfragen der Oberfläche, beantwortet durch E15 bis E19 (Run-Header, Proof Graph, Inspector, Agent Explorer, Timeline) |
| §1.2 | Fünf UX-Prinzipien | F-15.08 |  |
| §1.3 | Wichtige fachliche Grenze | F-01.07 | Zusätzlich Glossar und Invariante in AGENTS.md |
| §2 | Informationsarchitektur und Navigation | keine | Oberabschnitt, siehe Unterabschnitte |
| §2.1 | Hauptseiten | F-07.15, F-15.11, F-15.12, F-18.07, F-21.05, F-21.06, F-21.08, F-21.10, F-24.03 |  |
| §2.2 | Linke globale Navigation | F-15.02, F-18.07, F-21.09, F-21.11 |  |
| §3 | Live Research Workspace und Layout | keine | Oberabschnitt, siehe Unterabschnitte |
| §3.1 | Bildschirmkomposition | F-15.03, F-15.07, F-18.01, F-19.01, F-19.05 |  |
| §3.2 | Kopfbereich eines Forschungsruns | F-01.06, F-15.04 |  |
| §3.3 | Beispiel für die aktuelle Forschungsansicht | F-11.04, F-15.05 |  |
| §4 | Proof Search Graph | keine | Oberabschnitt, siehe Unterabschnitte |
| §4.1 | Struktur des Beweisgraphen | F-08.02, F-16.01 |  |
| §4.2 | Darstellung der Proof-Knoten | F-16.02 |  |
| §4.3 | Knotenstatus | F-01.07, F-15.06, F-16.02 |  |
| §4.4 | Interaktionen | F-16.03, F-16.04, F-16.06, F-16.07, F-16.08 |  |
| §5 | Agent Execution Graph und Agent Explorer | F-18.03 |  |
| §5.1 | Beispiel | F-18.03 |  |
| §5.2 | Agentenkarte | F-07.15, F-18.02 |  |
| §5.3 | Agentenaktionen | F-14.04, F-18.06, F-20.05, F-20.06 |  |
| §6 | Mathematical Knowledge Graph | F-21.01 |  |
| §6.1 | Knotentypen | F-10.01, F-21.01 |  |
| §6.2 | Beziehungstypen | F-10.02, F-10.04, F-10.11, F-21.01 |  |
| §6.3 | Interaktionen | F-10.04, F-21.02 |  |
| §7 | Inspector und mathematische Detailansichten | keine | Oberabschnitt, siehe Unterabschnitte |
| §7.1 | Inspector für Beweisschritte | F-13.06, F-17.01, F-17.02, F-17.03, F-17.04, F-17.05, F-17.06, F-17.07 |  |
| §7.2 | Inspector für mathematische Hypothesen | F-17.08 |  |
| §7.3 | Inspector für Agenten | F-17.09, F-24.02 |  |
| §8 | Echtzeitereignisse und Timeline | keine | Oberabschnitt, siehe Unterabschnitte |
| §8.1 | Event-Beispiele | F-02.02, F-16.05, F-19.01 |  |
| §8.2 | Timeline-Ansichten | F-19.03 |  |
| §8.3 | Timeline-Filter | F-16.06, F-19.02, F-19.04 |  |
| §9 | Replay und historische Zustände | keine | Oberabschnitt, siehe Unterabschnitte |
| §9.1 | Interaktiver Zeitregler | F-19.06 |  |
| §9.2 | Replay-Verhalten | F-19.06 |  |
| §9.3 | Technische Umsetzung | F-02.03, F-02.06, F-19.06, F-19.07, F-19.08 |  |
| §10 | Aktive Steuerung und Human-in-the-Loop | F-20.11 |  |
| §10.1 | Aktionen | F-08.05, F-19.08, F-20.01, F-20.03, F-20.04, F-20.05, F-20.06, F-20.07, F-20.08 |  |
| §10.2 | Kontrollierte Kommandos | F-14.04, F-14.05, F-20.09 |  |
| §10.3 | Beispielinteraktion | F-20.04 |  |
| §11 | Simulationen und symbolische Mathematik | keine | Oberabschnitt, siehe Unterabschnitte |
| §11.1 | Symbolic Workspace | F-05.02, F-21.03 |  |
| §11.2 | Simulation Workspace | F-05.04, F-21.04, F-21.10 |  |
| §11.3 | Beispiel | F-05.05, F-21.04 |  |
| §12 | Metriken und Dashboards | keine | Oberabschnitt, siehe Unterabschnitte |
| §12.1 | Run-Kennzahlen | F-09.05, F-15.05, F-18.04, F-21.07, F-23.05 |  |
| §12.2 | Wissenschaftliche Qualitätsmetriken | F-10.09, F-11.09, F-21.07 |  |
| §13 | Weitere Seiten und Funktionen | keine | Oberabschnitt, siehe Unterabschnitte |
| §13.1 | Research Overview | F-15.11 |  |
| §13.2 | Proof Explorer | F-21.05 |  |
| §13.3 | Model & Benchmark Laboratory | F-12.13, F-21.06 |  |
| §13.4 | Research Reports | F-13.04, F-13.05, F-21.08 |  |
| §13.5 | Workflow Builder (später) | F-22.01, F-22.02 |  |
| §14 | Designsystem und UX-Regeln | keine | Oberabschnitt, siehe Unterabschnitte |
| §14.1 | Visuelle Richtung | F-15.06 |  |
| §14.2 | Design Tokens | F-15.06 |  |
| §14.3 | Adaptive Detailtiefe | F-15.08 |  |
| §14.4 | UX-Regeln | F-15.10, F-15.14, F-16.06, F-19.07, F-20.09 |  |
| §15 | Frontend- und Echtzeitarchitektur | keine | Oberabschnitt, siehe Unterabschnitte |
| §15.1 | Architekturdiagramm | F-14.11 |  |
| §15.2 | Datenkanäle | F-14.03, F-14.10, F-14.11 |  |
| §15.3 | Frontend-State-Management | F-02.05, F-15.09 |  |
| §16 | Event-Schemas und API-Kontrakte | keine | Oberabschnitt, siehe Unterabschnitte |
| §16.1 | Beispielevent | F-02.01 |  |
| §16.2 | Technische Pflichtfelder | F-02.01, F-02.09, F-23.01, F-24.04 |  |
| §16.3 | Commands | F-14.04 |  |
| §16.4 | API-Entwurf (illustrativ) | F-02.07, F-02.09, F-14.01, F-14.02, F-14.03, F-14.06, F-14.08 |  |
| §17 | Tracing, Observability und Persistenz | keine | Oberabschnitt, siehe Unterabschnitte |
| §17.1 | Zwei unterschiedliche Tracing-Dimensionen | F-18.05, F-23.02, F-23.03, F-23.04 |  |
| §17.2 | Persistenzprinzipien | F-02.03, F-02.04, F-02.06, F-02.07, F-14.03, F-14.06 |  |
| §18 | Performance, Sicherheit und Zuverlässigkeit | keine | Oberabschnitt, siehe Unterabschnitte |
| §18.1 | Große Graphen | F-16.05, F-16.09 |  |
| §18.2 | Fehlerfälle | F-02.07, F-02.08, F-14.05, F-14.06, F-14.07, F-19.07 |  |
| §18.3 | Sicherheit | F-20.02, F-20.09, F-20.10, F-24.01, F-24.02, F-24.03, F-24.04, F-24.05, F-24.06, F-24.07 |  |
| §19 | Technologieauswahl und Plattformstrategie | F-00.01, F-14.01, F-15.01, F-15.10, F-15.13, F-17.03, F-21.01, F-21.04, F-23.02, F-23.03 | Technikempfehlungen, Plattformwahl offen in OD-01 |
| §19.1 | Empfehlung für die bestehenden Flutter-Projekte | F-15.01, F-15.13 | Widerspruch zu ARCH §17.1, offen in OD-01 |
| §19.2 | Performance-Hinweis | F-00.03, F-15.01, F-16.09 |  |
| §20 | MVP, Ausbaustufen und Akzeptanzkriterien | F-02.06, F-02.08, F-04.08, F-10.03, F-15.12, F-16.04, F-16.05, F-16.08, F-17.05, F-18.01, F-18.08, F-19.01, F-19.09, F-20.01, F-20.03, F-20.04, F-21.01, F-21.04, F-22.01, F-22.02, F-22.03, F-22.04, F-22.05, F-22.06, F-22.07, F-22.08 | Stufen und Kriterien, siehe ROADMAP.md |
| §20 Stufe 1 | Live Research Workspace (MVP) | F-18.01, F-19.01, F-20.01 |  |
| §20 Stufe 2 | Research Intelligence | F-10.03, F-16.04, F-16.08, F-18.08, F-20.03, F-20.04, F-21.01, F-21.04 |  |
| §20 Stufe 3 | Visual Research Orchestration | F-12.06, F-15.12, F-22.01, F-22.02, F-22.03, F-22.04, F-22.05, F-22.06, F-22.07, F-22.08 |  |
| §21 | Konkrete Entwicklungsaufgaben | F-02.08, F-14.03, F-14.04, F-15.03, F-15.04, F-15.05, F-15.06, F-15.07, F-16.01, F-16.02, F-16.03, F-16.05, F-16.06, F-16.09, F-17.01, F-17.02, F-17.03, F-17.04, F-17.05, F-17.07, F-18.01, F-18.04, F-18.05, F-18.06, F-19.02, F-19.03, F-19.06, F-19.08, F-19.09, F-20.01, F-20.02, F-20.05, F-20.10, F-21.01, F-21.03, F-21.04, F-21.08, F-23.04 | Checklisten der Epics UI-01 bis UI-08, siehe Unterzeilen |
| §21 Epic UI-01 | Domain Event Pipeline | F-02.01, F-02.03, F-02.04, F-02.06, F-02.08, F-14.03 |  |
| §21 Epic UI-02 | Research Shell | F-15.03, F-15.04, F-15.05, F-15.06, F-15.07 |  |
| §21 Epic UI-03 | Proof Graph | F-16.01, F-16.02, F-16.03, F-16.05, F-16.06, F-16.09 |  |
| §21 Epic UI-04 | Inspector | F-17.01, F-17.02, F-17.03, F-17.04, F-17.05, F-17.07 |  |
| §21 Epic UI-05 | Agent Explorer | F-18.01, F-18.04, F-18.05, F-18.06, F-23.04 |  |
| §21 Epic UI-06 | Timeline und Replay | F-19.02, F-19.03, F-19.06, F-19.08, F-19.09 |  |
| §21 Epic UI-07 | Human-in-the-Loop | F-14.04, F-20.01, F-20.02, F-20.05, F-20.10 |  |
| §21 Epic UI-08 | Knowledge & Experiment Laboratory | F-21.01, F-21.03, F-21.04, F-21.08 |  |
| §22 | Quellen und technische Referenzen | keine | Referenz |

## Ergänzungen ohne direkte Quelle

Einige Akzeptanzkriterien legen Werte fest, die die Quellen offenlassen. Sie sind im Feature als Festlegung oder Annahme des Backlogs gekennzeichnet, etwa WCAG AA in F-15.06, die Testgröße von 5000 Knoten in F-16.09, Kommandonamen in F-20.01 und die reine Anzeigefunktion der Console in F-19.05.
