# E12 Metriken, Reward und Lernverfahren

- Status: `todo` · Meilenstein: M4, Vorstufen M1 und M2, Ausbau M6
- Quellen: ARCH §2.4, §6.1, §10, §17.1, §17.3, §19 (Phase 4), §20 (Beiträge C und E), §21; UI §13.3
- Abhängige Epics: E08, E09, E11

## Ziel

Harte Korrektheitsmetriken und weiche Steuerungsmetriken bleiben getrennt. Policy- und Value-Modelle werden nur aus geprüften, versionierten Daten gelernt und nur übernommen, wenn sie auf unberührten Tests messbar besser sind und keine Regressionsregel verletzen.

## Abgrenzung

Benchmarkmetriken und Vergleiche liegen in E11, die Erhebung der Run-Daten in E09, die UI des Model Lab in F-21.06. Das Transfer Model liegt in F-10.12.

## Invarianten

Ungeprüfte neue Erkenntnisse verändern nie direkt Modellgewichte (ARCH §10.4). Formaler Gesamterfolg und unerlaubte Axiome werden hart behandelt. Hilfsmetriken dienen der Suchsteuerung und dürfen nicht zu Reward Hacking führen (ARCH §10.3). Mehrere Zielgrößen werden nicht vorschnell zu einer gewichteten Zahl zusammengezogen. Training und Produktivbetrieb sind entkoppelt.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-12.01 | Metrikebenen | `ready` | P0 | M2 |
| F-12.02 | Policy-Baseline | `todo` | P1 | M4 |
| F-12.03 | Value Model V(s,b) | `todo` | P1 | M4 |
| F-12.04 | Reward-Funktion und Potential-Based Shaping | `todo` | P1 | M4 |
| F-12.05 | Reward-Ablationen | `todo` | P1 | M4 |
| F-12.06 | Taktikbasierte Lernsignale | `todo` | P1 | M4 |
| F-12.07 | Replay Buffer | `todo` | P1 | M4 |
| F-12.08 | Replay-Daten markieren | `ready` | P1 | M2 |
| F-12.09 | Lernstufen SFT, Preference Learning und RL | `todo` | P1 | M4 |
| F-12.10 | Benchmark für lokale Modelle, Quantisierung und Kontext | `todo` | P1 | M1 |
| F-12.11 | Continual Learning und Forgetting-Tests | `todo` | P1 | M4 |
| F-12.12 | Lernender Meta Controller | `todo` | P2 | M6 |
| F-12.13 | Modellregistry und Übernahmegate | `todo` | P0 | M4 |

## Features

### F-12.01 Metrikebenen

- Status: `ready` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-09.05
- Quelle: ARCH §10.1
- Bearbeiter: offen · Nachweise: offen

Die sieben Metrikebenen aus ARCH §10.1 als getrennte, typisierte Gruppen.

| Ebene | Metriken |
| --- | --- |
| Korrektheit | Formal Success, ungültige Aktionen, offene Beweispflichten, unerwünschte Axiome |
| Fortschritt | Formal verifizierte Teilziele, Value-Schätzung, wiederverwendbare Lemmata |
| Kosten | Zeit bis Beweis, CPU- und GPU-Stunden, Tokens, Speicher, Modellaufrufe |
| Suchverhalten | Branches, Repeats, Tiefe, Backtracks, Strategievielfalt, Stoppgrund |
| Wissensgewinn | Verifizierte neue Lemmata, geprüfte Gegenbeispiele, wiederverwendete Methoden |
| Beweisqualität | Länge, Verständlichkeit, Rechenaufwand, Eleganz, Diversität |
| Generalisierung | Erfolg auf Varianten, Transfer zwischen Problemklassen, OOD-Robustheit |

- [ ] Jede Metrik gehört genau einer Ebene an und ist als hart oder weich markiert.
- [ ] Ein Fortschrittswert auf Basis der Subgoal-Anzahl ist ausgeschlossen (vgl. F-09.07).

### F-12.02 Policy-Baseline

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.07, F-11.03
- Quelle: ARCH §19 (Phase 4), §6.1 (Policy Model)
- Bearbeiter: offen · Nachweise: offen

Eine erste gelernte Policy, die Aktionen oder Strategien für einen Proof State vorschlägt, mit einer einfachen, reproduzierbaren Baseline als Vergleich.

- [ ] Die Baseline ist auf der Golden Suite bei festem Budget gemessen (F-11.10).

### F-12.03 Value Model V(s,b)

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.01, F-12.07
- Quelle: ARCH §10.2, §6.1; HTPS in ARCH §2.1
- Bearbeiter: offen · Nachweise: offen

V(s,b) schätzt die Wahrscheinlichkeit eines vollständigen Beweises im verbleibenden Budget b ausgehend vom Zustand s. Kalibrierung gegen historische Suchverläufe, bekannte Abschlusszustände und zensierte Zeitlimits. Getrennte Schätzungen pro Domäne und Strategie sind möglich. Der Wert wird in UI und Metriken immer als Schätzung gekennzeichnet.

- [ ] Ein Kalibrierungsbericht (zum Beispiel Reliability-Diagramm) liegt pro Version vor.
- [ ] Zensierte Läufe werden in der Kalibrierung als zensiert behandelt.

### F-12.04 Reward-Funktion und Potential-Based Shaping

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.01
- Quelle: ARCH §10.3
- Bearbeiter: offen · Nachweise: offen

R = w_s·R_success + w_v·R_verified + w_p·R_progress + w_n·R_novelty − w_c·C_compute − w_e·C_errors als konfigurierbare Designhypothese. Optional Potential-Based Shaping r'_t = r_t + γΦ(s_{t+1}) − Φ(s_t).

- [ ] Gewichte sind versioniert und Teil jedes Trainingslaufs.
- [ ] Ein Test zeigt, dass unerlaubte Axiome unabhängig von den Gewichten zu einem harten Ausschluss führen.

### F-12.05 Reward-Ablationen

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.04, F-11.11
- Quelle: ARCH §19 (Phase 4), §10.3
- Bearbeiter: offen · Nachweise: offen

Systematischer Vergleich von Reward-Varianten, um Reward Hacking und Fehlanreize zu erkennen.

- [ ] Jede Variante ist mit Seeds und Konfidenzintervall ausgewertet (F-11.12).

### F-12.06 Taktikbasierte Lernsignale

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.07, F-04.04
- Quelle: ARCH §10.4 (Stufe 3), §19 (Phase 4); Process-Verified RL in ARCH §2.4
- Bearbeiter: offen · Nachweise: offen

Lean-Feedback pro Taktik als dichteres Signal statt nur Endergebnis.

- [ ] Jedes Signal ist an einen geprüften Lean-Schritt gebunden.

### F-12.07 Replay Buffer

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.08
- Quelle: ARCH §19 (Phase 4), §10.4 (Stufe 4)
- Bearbeiter: offen · Nachweise: offen

Versionierter Datensatz aus markierten Versuchen mit DVC, getrennt nach Problemfamilien gemäß F-11.08.

- [ ] Jede Datensatzversion ist unveränderlich und reproduzierbar erzeugt.

### F-12.08 Replay-Daten markieren

- Status: `ready` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-09.01
- Quelle: ARCH §7.4 (Schritt 5)
- Bearbeiter: offen · Nachweise: offen

Workflow D markiert geeignete Versuche für spätere Trainingsläufe. Es findet kein Training im Produktivbetrieb statt.

- [ ] Markierungen enthalten Version, Kontext und Verifikationsstatus.
- [ ] Unverifizierte Ergebnisse werden als solche markiert und sind von SFT-Daten ausgeschlossen.

### F-12.09 Lernstufen SFT, Preference Learning und RL

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.07, F-12.13
- Quelle: ARCH §10.4 (Stufen 1 bis 3), §19 (Phase 4, SFT/RL-Pipeline)
- Bearbeiter: offen · Nachweise: offen

Stufe 1 trainiert supervised auf formal bewiesenen Aufgaben. Stufe 2 bevorzugt unter gleichen Budgets effizientere Strategien (Imitation oder Preference Learning). Stufe 3 optimiert Policy und Value über geprüfte Lean-Interaktionen mit Taktik-Feedback (F-12.06). Training läuft mit PyTorch, Hyperparameter mit Optuna, verteilte Läufe mit Ray erst bei Bedarf (ARCH §17.2).

- [ ] Jede Stufe ist als reproduzierbare Pipeline mit gepinnten Daten und Seeds lauffähig.

### F-12.10 Benchmark für lokale Modelle, Quantisierung und Kontext

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-07.01 (OD-03)
- Quelle: ARCH §17.3
- Bearbeiter: offen · Nachweise: offen

Die sechs Hardwarepunkte aus ARCH §17.3 werden gemessen, also welche Modellgrößen, Quantisierungen und Kontextfenster auf der lokalen GPU mit 8 GB lauffähig sind und was in die Cloud ausgelagert werden muss. Dazu die Lizenzprüfung jedes Modells. Das Ergebnis speist OD-03.

- [ ] Ein Bericht mit Latenz, Speicherbedarf und Erfolgsquote pro Modell und Quantisierung liegt vor.
- [ ] Jedes Modell ist mit Lizenz im Inventar (F-00.07) erfasst.

### F-12.11 Continual Learning und Forgetting-Tests

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-12.09
- Quelle: ARCH §10.4 (Stufe 4), §19 (Phase 4, Catastrophic-Forgetting-Tests), §20 (Beitrag E)
- Bearbeiter: offen · Nachweise: offen

Neue Erfahrungen fließen in kontrollierten Trainingszyklen ein, mit Regressionstests und Replay. Retention, Forward und Backward Transfer werden gemessen.

- [ ] Ein Trainingszyklus, der alte Aufgaben verschlechtert, wird vom Gate (F-12.13) abgelehnt.

### F-12.12 Lernender Meta Controller

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-08.04, F-12.03
- Quelle: ARCH §6.1 (Meta Controller), §20 (Beitrag C)
- Bearbeiter: offen · Nachweise: offen

Ersetzt oder ergänzt den regelbasierten Budget Controller (F-08.04) durch eine gelernte Ressourcenzuteilung.

- [ ] Pass@Budget und Time-to-Proof sind gegenüber dem regelbasierten Controller bei gleichem Budget verglichen.

### F-12.13 Modellregistry und Übernahmegate

- Status: `todo` · Priorität: P0 · Meilenstein: M4
- Abhängigkeiten: F-11.03, F-11.08
- Quelle: ARCH §19 (Phase 4, Akzeptanz), §10.4 (letzter Absatz), §17.1 (MLflow, DVC); UI §13.3
- Bearbeiter: offen · Nachweise: offen

Modelle, Datensätze und Trainingsläufe werden in MLflow und DVC versioniert. Ein neues Modell wird nur übernommen, wenn es auf unberührten Testmengen messbar besser ist und keine Regressionsregel verletzt.

- [ ] Abnahme M4: Ein Modellwechsel ohne bestandenes Gate ist technisch nicht möglich.
- [ ] Jedes Modell ist auf Trainingsdaten, Code-Commit und Evaluation zurückführbar.
