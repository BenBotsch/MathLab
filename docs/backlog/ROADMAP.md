# Roadmap

Die Meilensteine M1 bis M6 verbinden die Entwicklungsphasen aus ARCH §19 mit den Ausbaustufen der Oberfläche aus UI §20. Die Reihenfolge folgt ARCH §22. Zuerst entsteht die kleinste vollständig nachvollziehbare Beweisumgebung, ein eigenes großes Mathematikmodell wird nicht trainiert. Lernverfahren kommen erst, wenn genug Daten vorliegen.

Ein Meilenstein ist erreicht, wenn alle seine P0-Features `done` sind und jedes Exit-Kriterium einen ausgeführten Nachweis hat. Die Zeitangaben aus ARCH §19 sind grobe Planungsannahmen. Forschungsteile können erheblich länger dauern.

Die Feature-Tabellen dieser Datei spiegeln die Epic-Dateien. Bei Abweichungen gilt die Epic-Datei.

| Meilenstein | Inhalt | Quelle | Features |
| --- | --- | --- | --- |
| [M1](#m1) | Proof Engine MVP und Live Research Workspace | ARCH Phase 1, UI Stufe 1 | 119 |
| [M2](#m2) | Mehrere Agenten und Methoden, Research Intelligence | ARCH Phase 2, UI Stufe 2 | 75 |
| [M3](#m3) | Wissensgraph und Langzeitgedächtnis | ARCH Phase 3 | 14 |
| [M4](#m4) | ML und RL | ARCH Phase 4 | 13 |
| [M5](#m5) | Dashboards, Simulation und Erklärungen | ARCH Phase 5 | 17 |
| [M6](#m6) | Eigenständige Forschung und visuelle Orchestrierung | ARCH Phase 6, UI Stufe 3 | 25 |

## M1

Proof Engine MVP und Live Research Workspace. Grob 4 bis 6 Wochen laut ARCH §19. Eine fixierte Liste von 20 bis 50 Aufgaben wird mit Lean 4, Mathlib, SymPy und einem Tactic-Agenten bearbeitet. Alle ProofAttempt-Events werden erfasst, und eine CLI sowie der Live Research Workspace machen den Ablauf sichtbar.

Voraussetzung sind die Entscheidungen OD-01 bis OD-07 aus [OPEN_DECISIONS.md](../decisions/OPEN_DECISIONS.md). F-00.01 bereitet sie vor, F-11.01 erarbeitet die Golden-Problemliste.

Exit-Kriterien aus ARCH §19, Phase 1. Die ersten drei Zeilen sind die dort genannte Akzeptanz, die letzten zwei folgen aus der Inhaltsliste der Phase und aus ARCH §22, Schritt 6.

| Kriterium | Nachweis durch |
| --- | --- |
| Jede Aufgabe hat einen unveränderlichen Zielhash. | F-01.03, F-03.02 |
| Alle Versuche und Verifikationen sind reproduzierbar. | F-00.03, F-04.03, F-09.02 |
| Mindestens eine End-to-End-Lösung besteht. Referenz ist die Summe ungerader Zahlen aus ARCH §15. | F-11.04 |
| Erfolgsquote, Zeit, Tokens und Fehler werden gemessen. | F-09.05, F-23.05 |
| Die Golden Suite läuft als Regressionsgate. | F-11.03 |

Exit-Kriterien aus UI §20, Stufe 1:

| Nr. | Kriterium | Nachweis durch |
| --- | --- | --- |
| 1 | Ein Agentenevent erscheint während der Ausführung in der Timeline. | F-14.03, F-19.01 |
| 2 | `proof.step.verified` aktualisiert den verknüpften Beweisknoten. | F-04.08, F-16.05 |
| 3 | Der Inspector zeigt für jeden Schritt Provenienz und Verifikationsstatus. | F-17.04, F-17.05 |
| 4 | Ein Browser- oder Client-Neustart verliert keine abgeschlossenen Events. | F-02.08, F-15.09 |
| 5 | Replay erzeugt denselben historischen UI-Zustand aus Snapshot und Eventfolge. | F-02.06, F-19.07, F-19.09 |
| 6 | Pausieren und Fortsetzen werden serverseitig bestätigt und vollständig protokolliert. | F-14.04, F-20.01 |
| 7 | Nicht geprüfte Lemmata sind niemals als formal bewiesen dargestellt. | F-01.07, F-16.02 |

| Epic | P0 | P1 | P2 |
| --- | --- | --- | --- |
| [E00](epics/E00-projektfundament.md) | F-00.01, F-00.02, F-00.03, F-00.04, F-00.05 | F-00.07, F-00.08, F-00.09 | keine |
| [E01](epics/E01-core-domaenenmodell.md) | F-01.01, F-01.02, F-01.03, F-01.04, F-01.05, F-01.06, F-01.07 | keine | keine |
| [E02](epics/E02-event-sourcing-persistenz.md) | F-02.01, F-02.02, F-02.03, F-02.04, F-02.05, F-02.06, F-02.07, F-02.08 | keine | keine |
| [E03](epics/E03-problem-engine.md) | F-03.01, F-03.02, F-03.05 | F-03.03, F-03.10, F-03.12 | keine |
| [E04](epics/E04-formal-verification.md) | F-04.01, F-04.02, F-04.03, F-04.04, F-04.05, F-04.07, F-04.08, F-04.11 | F-04.06 | keine |
| [E05](epics/E05-symbolik-smt-numerik.md) | F-05.01, F-05.02, F-05.07 | keine | keine |
| [E07](epics/E07-agent-orchestrator.md) | F-07.01, F-07.02, F-07.03, F-07.04, F-07.05, F-07.09 | F-07.16 | keine |
| [E08](epics/E08-proof-search.md) | F-08.01, F-08.02, F-08.03, F-08.04, F-08.05 | keine | keine |
| [E09](epics/E09-trial-and-error-tracking.md) | F-09.01, F-09.02, F-09.03, F-09.05 | keine | keine |
| [E11](epics/E11-benchmarks-evaluation.md) | F-11.01, F-11.02, F-11.03, F-11.04, F-11.09 | keine | keine |
| [E12](epics/E12-metriken-lernen.md) | keine | F-12.10 | keine |
| [E14](epics/E14-backend-api.md) | F-14.01, F-14.02, F-14.03, F-14.04, F-14.05, F-14.06, F-14.07, F-14.09, F-14.11, F-14.12, F-14.13, F-14.14 | keine | keine |
| [E15](epics/E15-research-shell.md) | F-15.01, F-15.02, F-15.03, F-15.04, F-15.05, F-15.06, F-15.09 | F-15.07, F-15.10 | keine |
| [E16](epics/E16-proof-graph-ui.md) | F-16.01, F-16.02, F-16.03, F-16.05, F-16.06 | F-16.04, F-16.09 | keine |
| [E17](epics/E17-inspector.md) | F-17.01, F-17.02, F-17.03, F-17.04, F-17.05 | F-17.06, F-17.09 | keine |
| [E18](epics/E18-agent-explorer.md) | F-18.01, F-18.02 | F-18.03, F-18.04 | keine |
| [E19](epics/E19-timeline-replay.md) | F-19.01, F-19.02, F-19.06, F-19.07, F-19.09 | F-19.04, F-19.05 | keine |
| [E20](epics/E20-human-in-the-loop.md) | F-20.01, F-20.09, F-20.10 | F-20.02 | keine |
| [E23](epics/E23-observability.md) | F-23.01, F-23.05 | keine | keine |
| [E24](epics/E24-sicherheit-sandbox.md) | F-24.01, F-24.02, F-24.03, F-24.04, F-24.06, F-24.07, F-24.09 | keine | keine |

### Reihenfolge in M1

Die Stufen ergeben sich aus den Feature-Abhängigkeiten. Ein Feature einer Stufe hängt nur von Features früherer Stufen ab. Features derselben Stufe können parallel bearbeitet werden, sobald ihre offenen Entscheidungen getroffen sind.

| Stufe | Features |
| --- | --- |
| 0 | F-00.01, F-00.07, F-11.01, F-24.09 |
| 1 | F-00.02 |
| 2 | F-00.03, F-00.05, F-01.01, F-01.02, F-15.01 |
| 3 | F-00.04, F-01.03, F-01.04, F-01.05, F-01.06, F-01.07, F-02.01, F-02.07, F-03.01, F-04.11, F-05.07, F-14.01, F-15.02, F-15.03, F-15.06 |
| 4 | F-00.08, F-00.09, F-02.02, F-02.03, F-03.02, F-04.01, F-07.01, F-07.16, F-15.07, F-15.10, F-23.01, F-24.01, F-24.02, F-24.03, F-24.04 |
| 5 | F-02.04, F-02.05, F-03.03, F-03.05, F-04.02, F-05.01, F-07.02, F-09.01, F-12.10, F-14.03, F-14.11, F-23.05 |
| 6 | F-02.06, F-04.03, F-05.02, F-07.03, F-08.01, F-09.02, F-09.03, F-09.05, F-14.06, F-15.09, F-19.01 |
| 7 | F-02.08, F-04.04, F-04.05, F-07.04, F-07.05, F-08.02, F-11.09, F-14.02, F-14.04, F-18.01, F-19.02, F-19.05, F-19.06 |
| 8 | F-04.06, F-04.07, F-04.08, F-07.09, F-08.03, F-08.04, F-08.05, F-11.02, F-11.03, F-11.04, F-14.05, F-14.07, F-15.04, F-16.01, F-18.02, F-18.03, F-19.07, F-19.09, F-20.10, F-24.07 |
| 9 | F-14.12, F-15.05, F-16.02, F-16.05, F-17.09, F-18.04, F-20.01, F-24.06 |
| 10 | F-14.09, F-14.13, F-14.14, F-16.03, F-16.04, F-16.06, F-16.09, F-20.02, F-20.09 |
| 11 | F-17.01, F-19.04 |
| 12 | F-17.02, F-17.03, F-17.04, F-17.05, F-17.06 |

## M2

Mehrere Agenten und Beweismethoden sowie Research Intelligence. Grob weitere 4 bis 8 Wochen laut ARCH §19. Strategy Registry, Agentenrollen und Budget Controller kommen hinzu, außerdem mindestens drei Methodenstrategien, parallele und Best-First-Suche, Teilzielzerlegung, Fehlerklassifikation und Retries. Die Oberfläche erhält Proof-Vergleiche, Agentenvergleiche, Graphfilter und Suchzweig-Priorisierung.

Exit-Kriterien aus ARCH §19, Phase 2:

| Kriterium | Nachweis durch |
| --- | --- |
| Unterschiedliche Strategien werden mit festen Budgets verglichen. | F-06.03, F-11.10 |
| Runs sind pausierbar und wiederaufnehmbar. | F-08.05, F-20.01 |

Exit-Kriterien aus UI §20, Stufe 2:

| Kriterium | Nachweis durch |
| --- | --- |
| Ein verifiziertes Lemma ist zwischen Proof- und Knowledge-Graph auffindbar. | F-10.03, F-21.01 |
| Zwei unterschiedliche Beweise desselben Zielstatements können verglichen werden. | F-16.08 |
| Die Simulation zeigt Parameter, Modell, Seed, Präzision und Ergebnisstatus. | F-21.04 |
| Eine Benutzeranweisung für einen neuen Suchzweig erzeugt einen neuen, auditierbaren Attempt. | F-20.03, F-20.04 |

Der Wissensgraph aus UI Stufe 2 entsteht in M2 nur als Vorstufe. Sein vollständiger Ausbau liegt in M3.

| Epic | P0 | P1 | P2 |
| --- | --- | --- | --- |
| [E00](epics/E00-projektfundament.md) | keine | F-00.06 | keine |
| [E02](epics/E02-event-sourcing-persistenz.md) | keine | F-02.09, F-02.10 | keine |
| [E03](epics/E03-problem-engine.md) | keine | F-03.04, F-03.06, F-03.07, F-03.08, F-03.11 | keine |
| [E04](epics/E04-formal-verification.md) | keine | F-04.09, F-04.10, F-04.12, F-04.13, F-04.14, F-04.15, F-04.16 | keine |
| [E05](epics/E05-symbolik-smt-numerik.md) | keine | F-05.03, F-05.04, F-05.05, F-05.06 | keine |
| [E06](epics/E06-strategy-engine.md) | F-06.01, F-06.02, F-06.03 | F-06.05, F-06.06 | keine |
| [E07](epics/E07-agent-orchestrator.md) | keine | F-07.06, F-07.07, F-07.08, F-07.10, F-07.13, F-07.15 | keine |
| [E08](epics/E08-proof-search.md) | keine | F-08.06, F-08.07, F-08.08, F-08.10, F-08.12, F-08.13 | keine |
| [E09](epics/E09-trial-and-error-tracking.md) | keine | F-09.04, F-09.06, F-09.08 | keine |
| [E10](epics/E10-wissensgraph.md) | F-10.01, F-10.02, F-10.03 | keine | keine |
| [E11](epics/E11-benchmarks-evaluation.md) | F-11.08, F-11.10 | F-11.05, F-11.06, F-11.07, F-11.12, F-11.14, F-11.15 | keine |
| [E12](epics/E12-metriken-lernen.md) | F-12.01 | F-12.08 | keine |
| [E13](epics/E13-explanation-reports.md) | keine | F-13.01, F-13.04 | keine |
| [E15](epics/E15-research-shell.md) | F-15.11 | F-15.08, F-15.12 | keine |
| [E16](epics/E16-proof-graph-ui.md) | keine | F-16.07, F-16.08 | keine |
| [E17](epics/E17-inspector.md) | keine | F-17.07, F-17.08 | keine |
| [E18](epics/E18-agent-explorer.md) | keine | F-18.05, F-18.06, F-18.07 | F-18.08 |
| [E19](epics/E19-timeline-replay.md) | keine | F-19.03, F-19.08, F-19.10 | keine |
| [E20](epics/E20-human-in-the-loop.md) | keine | F-20.03, F-20.04, F-20.05, F-20.06, F-20.07, F-20.08, F-20.11 | keine |
| [E21](epics/E21-labs-ui.md) | F-21.05 | F-21.01, F-21.03, F-21.04, F-21.07, F-21.09 | keine |
| [E23](epics/E23-observability.md) | keine | F-23.02, F-23.04 | F-23.03 |
| [E24](epics/E24-sicherheit-sandbox.md) | keine | F-24.08 | keine |

## M3

Wissensgraph und Langzeitgedächtnis. Grob weitere 6 bis 10 Wochen laut ARCH §19. Theorem-, Lemma- und Problemgraph, exakte, semantische und graphbasierte Suche, strukturierte Fehlversuchs-Memory und problemübergreifender Abruf.

Exit-Kriterium aus ARCH §19, Phase 3:

| Kriterium | Nachweis durch |
| --- | --- |
| Ein nachgewiesenes Lemma wird bei einem zweiten Problem wiedergefunden und mit dokumentierter Provenienz erfolgreich angewendet. | F-10.06, F-10.09 |

| Epic | P0 | P1 | P2 |
| --- | --- | --- | --- |
| [E06](epics/E06-strategy-engine.md) | keine | F-06.04 | keine |
| [E07](epics/E07-agent-orchestrator.md) | keine | F-07.11 | keine |
| [E10](epics/E10-wissensgraph.md) | F-10.04, F-10.05, F-10.06, F-10.09 | F-10.07, F-10.08, F-10.10, F-10.11 | keine |
| [E14](epics/E14-backend-api.md) | keine | F-14.08 | keine |
| [E21](epics/E21-labs-ui.md) | keine | F-21.02, F-21.11 | keine |
| [E24](epics/E24-sicherheit-sandbox.md) | keine | F-24.05 | keine |

## M4

ML und RL. Policy- und Value-Baselines, Replay Buffer, Reward-Ablationen, taktikbasierte Lernsignale, eine kontrollierte Pipeline für SFT und RL sowie Tests auf Catastrophic Forgetting. Dieser Meilenstein beginnt erst, wenn aus M1 bis M3 ausreichend Daten vorliegen (ARCH §22, Schritt 9).

Exit-Kriterium aus ARCH §19, Phase 4:

| Kriterium | Nachweis durch |
| --- | --- |
| Eine neue Modellversion wird nur übernommen, wenn sie auf unberührten Tests messbar besser als die Baseline ist und keine kritische Regressionsregel verletzt. | F-12.11, F-12.13 |

| Epic | P0 | P1 | P2 |
| --- | --- | --- | --- |
| [E08](epics/E08-proof-search.md) | keine | F-08.09 | keine |
| [E09](epics/E09-trial-and-error-tracking.md) | keine | F-09.07 | keine |
| [E11](epics/E11-benchmarks-evaluation.md) | keine | F-11.11 | keine |
| [E12](epics/E12-metriken-lernen.md) | F-12.13 | F-12.02, F-12.03, F-12.04, F-12.05, F-12.06, F-12.07, F-12.09, F-12.11 | keine |
| [E21](epics/E21-labs-ui.md) | keine | F-21.06 | keine |

## M5

Dashboards, Simulation und Erklärungen. Proof Tree, Knowledge Graph, Parameterstudien, Agent Monitor und Model Laboratory, verständliche und zitierbare Erklärungen sowie Beweisexporte in Markdown, LaTeX und Lean.

Exit-Kriterium aus ARCH §19, Phase 5:

| Kriterium | Nachweis durch |
| --- | --- |
| Zu einem erfolgreichen Beweis sind Provenienz, verwendete Lemmata, alternative Strategien, Laufzeiten und eine menschlich lesbare Herleitung abrufbar. | F-13.03, F-13.04, F-13.05 |

| Epic | P0 | P1 | P2 |
| --- | --- | --- | --- |
| [E03](epics/E03-problem-engine.md) | keine | keine | F-03.09 |
| [E05](epics/E05-symbolik-smt-numerik.md) | keine | keine | F-05.08 |
| [E07](epics/E07-agent-orchestrator.md) | keine | keine | F-07.14 |
| [E11](epics/E11-benchmarks-evaluation.md) | keine | keine | F-11.16 |
| [E13](epics/E13-explanation-reports.md) | F-13.03 | F-13.02, F-13.05, F-13.06, F-13.10 | F-13.07, F-13.08, F-13.09, F-13.11 |
| [E15](epics/E15-research-shell.md) | keine | keine | F-15.13, F-15.14 |
| [E17](epics/E17-inspector.md) | keine | F-17.10 | keine |
| [E21](epics/E21-labs-ui.md) | keine | F-21.08, F-21.10 | keine |

## M6

Eigenständige Forschung und visuelle Orchestrierung. Neue Vermutungen, automatische Lemma-Extraktion, Methodentransfer zwischen Fachgebieten, forschungsnahe Benchmarks, Expertenreview und neue Publikationsfragen aus Ablationen. Dazu kommen Workflow-Editor, dynamische Strategieregeln und adaptive Budgetsteuerung aus UI Stufe 3. Die Forschungsbeiträge A bis E aus ARCH §20 sind Hypothesen und brauchen vor einer Veröffentlichung eine Neuheitsprüfung (F-25.01).

ARCH §19 nennt für Phase 6 keine Akzeptanzkriterien. Die Kriterien der einzelnen Features in E25 gelten deshalb als Exit-Kriterien.

Exit-Kriterien aus UI §20, Stufe 3:

| Kriterium | Nachweis durch |
| --- | --- |
| Ein Workflow kann visuell erstellt, validiert, versioniert und reproduzierbar ausgeführt werden. | F-22.01, F-22.02, F-22.03, F-22.04 |
| Änderungen an Workflows und Agentenprofilen werden gegen feste Golden Tests verglichen. | F-22.05 |
| Budgetentscheidungen und Strategieänderungen sind nachvollziehbar. | F-22.07 |

| Epic | P0 | P1 | P2 |
| --- | --- | --- | --- |
| [E05](epics/E05-symbolik-smt-numerik.md) | keine | keine | F-05.09 |
| [E07](epics/E07-agent-orchestrator.md) | keine | keine | F-07.12 |
| [E08](epics/E08-proof-search.md) | keine | keine | F-08.11 |
| [E10](epics/E10-wissensgraph.md) | keine | keine | F-10.12 |
| [E11](epics/E11-benchmarks-evaluation.md) | keine | keine | F-11.13 |
| [E12](epics/E12-metriken-lernen.md) | keine | keine | F-12.12 |
| [E14](epics/E14-backend-api.md) | keine | keine | F-14.10 |
| [E22](epics/E22-workflow-builder.md) | keine | F-22.01, F-22.03, F-22.04, F-22.05, F-22.07 | F-22.02, F-22.06, F-22.08 |
| [E25](epics/E25-forschungsbeitraege.md) | keine | F-25.01, F-25.02, F-25.04, F-25.07, F-25.08, F-25.09 | F-25.03, F-25.05, F-25.06, F-25.10 |

## Pflege

Bei jedem Meilenstein-Abschluss wird das Risikoregister in F-24.09 überprüft. Ein Feature wechselt den Meilenstein nur mit einem Vermerk im Feature und einer Anpassung dieser Datei. Ändert sich ein Status, eine Priorität oder eine Abhängigkeit, werden die Tabellen dieser Datei nachgezogen.
