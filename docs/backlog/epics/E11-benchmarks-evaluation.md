# E11 Benchmarks, Betriebsmodi und Evaluation

- Status: `todo` · Meilenstein: M1, Ausbau M2 bis M6
- Quellen: ARCH §1.1, §3.3, §4.1 (Experiment/Evaluation Engine), §15, §16, §19, §21, §21.1, §22; UI §12.2
- Abhängige Epics: E01, E04, E09

## Ziel

Fixierte, versionierte Benchmarks machen Methoden, Modelle und Konfigurationen objektiv vergleichbar. Betriebsmodi regeln, welche Informationen ein Run sehen darf. Kontamination, ungleiche Budgets und fehlende Streuungsangaben werden systematisch verhindert.

## Abgrenzung

Run-Metriken liegen in F-09.05, das Model & Benchmark Lab der UI in F-21.06, das Modelltraining in E12.

## Invarianten

Vergleiche laufen immer mit denselben Ressourcenbudgets, Toolchains und Solverlimits (ARCH §16.4). Referenzlösungen bleiben in `BLIND_REDISCOVERY` vollständig verborgen. Antwortentdeckung und formaler Beweis werden getrennt bewertet (ARCH §16.1). Testfälle und ihre Formalisierungen sind versioniert.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-11.01 | Golden-Problemliste für M1 ausarbeiten | `ready` | P0 | M1 |
| F-11.02 | Betriebsmodi durchsetzen | `todo` | P0 | M1 |
| F-11.03 | Golden-Suite-Runner und Regressionsgate | `todo` | P0 | M1 |
| F-11.04 | Referenzbeispiel Summe ungerader Zahlen | `todo` | P0 | M1 |
| F-11.05 | Spezialtests | `todo` | P1 | M2 |
| F-11.06 | Externe Benchmarks miniF2F, ProofNet und PutnamBench | `todo` | P1 | M2 |
| F-11.07 | Discover-and-Prove-Trennung | `todo` | P1 | M2 |
| F-11.08 | Kontaminations- und Leakage-Kontrollen | `todo` | P0 | M2 |
| F-11.09 | Benchmarkmetriken | `done` | P0 | M1 |
| F-11.10 | Strategievergleich bei festem Budget | `todo` | P0 | M2 |
| F-11.11 | Ablationsstudien | `todo` | P1 | M4 |
| F-11.12 | Seeds, Streuung und Konfidenzintervalle | `todo` | P1 | M2 |
| F-11.13 | Forschungsnahe Benchmarks | `todo` | P2 | M6 |
| F-11.14 | Evaluation Engine für Beweisvergleiche | `todo` | P1 | M2 |

## Features

### F-11.01 Golden-Problemliste für M1 ausarbeiten

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: keine
- Quelle: ARCH §16.2, §19 (Phase 1), §22 (Schritt 2)
- Bearbeiter: offen · Nachweise: offen

Ausarbeitung für OD-07. Eine fixierte Liste von 20 bis 50 Aufgaben der Level 1 bis 3 mit natürlicher Aussage, Lean-Zielaussage, Quelle, Lizenz, Level, Methodenhinweis und Kennzeichnung als Blind-Rediscovery-Holdout. Das Referenzbeispiel aus ARCH §15 ist enthalten.

- [ ] Die Liste liegt als versionierte Datei vor und ist in einem ADR für OD-07 bestätigt.
- [ ] Jede Aufgabe hat eine Lean-Aussage, die mit gepinnter Mathlib kompiliert (nach F-04.01).
- [ ] Holdout-Aufgaben sind markiert und ihre Referenzlösungen getrennt abgelegt.

### F-11.02 Betriebsmodi durchsetzen

- Status: `todo` · Priorität: P0 · Meilenstein: M1, alle Modi bis M6
- Abhängigkeiten: F-01.06, F-07.05
- Quelle: ARCH §3.3, §6.4, §16.4
- Bearbeiter: offen · Nachweise: offen

Die fünf Modi mit ihren kritischen Grenzen aus ARCH §3.3.

| Modus | Durchgesetzte Grenze |
| --- | --- |
| `BLIND_REDISCOVERY` | Referenzbeweis und bekannte Lösung bleiben verborgen |
| `ASSISTED_REDISCOVERY` | Bekannte Hilfssätze erlaubt, verwendete Ressourcen vollständig protokolliert |
| `ALTERNATIVE_PROOF` | Neuer Beweis muss sich methodisch unterscheiden (F-08.10) |
| `CONJECTURE_RESEARCH` | Empirische Evidenz wird von Beweisen unterschieden |
| `MATHEMATICAL_EXPLORATION` | Ergebnisse gelten zunächst nur als experimentelle Befunde |

M1 setzt `BLIND_REDISCOVERY` und `ASSISTED_REDISCOVERY` durch, `ALTERNATIVE_PROOF` folgt in M2, die beiden Forschungsmodi in M6 (E25).

- [ ] Ein Zugriff auf eine Referenzlösung im Blind-Modus wird abgelehnt und als Ereignis protokolliert.
- [ ] Im Assisted-Modus ist jede verwendete externe Ressource im Run abrufbar.

### F-11.03 Golden-Suite-Runner und Regressionsgate

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-11.01, F-09.05, F-07.04
- Quelle: ARCH §16.2, §21.1 (Golden-Benchmark-Smoke-Tests, Regressionen), §22 (Schritt 6)
- Bearbeiter: offen · Nachweise: offen

Führt die Golden Suite mit festem Budget aus und misst Pass@k, Kosten, Laufzeit und formale Validität. Ein Smoke-Lauf mit kleinem Budget läuft in CI (F-00.06), Regressionen bei Erfolgsquote und Kosten werden sichtbar.

- [ ] Ein Lauf erzeugt einen versionierten `EvaluationRun` mit allen Metriken.
- [ ] Der CI-Smoke-Lauf schlägt bei Regression gegenüber der Baseline fehl.

### F-11.04 Referenzbeispiel Summe ungerader Zahlen

- Status: `todo` · Priorität: P0 · Meilenstein: M1, Ausbau M2 und M5
- Abhängigkeiten: F-11.01, F-07.04, F-04.04
- Quelle: ARCH §15, §19 (Phase 1, Akzeptanz); UI §3.3
- Bearbeiter: offen · Nachweise: offen

End-to-End-Abnahmetest mit dem Ziel Σ(2k−1) = n². M1 verlangt einen verifizierten Beweis. M2 verlangt den algebraischen und den induktiven Beweisweg sowie die experimentelle Beobachtung als Hypothese. M5 ergänzt den geometrischen Weg und den Workflow aus ARCH §15.5 vollständig.

- [ ] M1: Ein formal verifizierter Beweis mit unveränderlichem Zielhash und reproduzierbaren Versuchen.
- [ ] M2: Algebraischer und induktiver Beweis sind getrennt verifiziert, die Tabelle aus ARCH §15.1 ist als `NUMERICALLY_SUPPORTED` gespeichert.
- [ ] M5: Alle acht Schritte aus ARCH §15.5 sind im Ereignisverlauf eines Runs nachvollziehbar.

Formeln aus ARCH §15, §15.2 und §15.3, unverändert zitiert. Bei Abweichung gilt die Quelle.

```latex
\[
\sum_{k=1}^{n}(2k-1)=n^2\qquad (n\in\mathbb{N},\ n\ge 1).
\]

\[
\begin{aligned}
\sum_{k=1}^{n}(2k-1)
&=2\sum_{k=1}^{n}k-n\\
&=2\cdot\frac{n(n+1)}2-n\\
&=n^2.
\end{aligned}
\]

\[
\begin{aligned}
\sum_{k=1}^{n+1}(2k-1)
&=n^2+(2n+1)\\
&=(n+1)^2.
\end{aligned}
\]
```

### F-11.05 Spezialtests

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-11.03
- Quelle: ARCH §16.2 (Spezialtests); Benchmarking Testing in ATP in ARCH §2.4
- Bearbeiter: offen · Nachweise: offen

Testaufgaben für falsche Aussagen, fehlende Voraussetzungen, mehrdeutige Texte, vorhandene Gegenbeispiele, alternative Beweise, verborgene Referenzlösungen, ähnliche aber nicht äquivalente Theoreme, problemübergreifendes Wiederverwenden und unvorhergesehene Suchbudgets.

- [ ] Jede der neun Kategorien hat mindestens eine Aufgabe mit erwartetem Ergebnis.
- [ ] Eine falsche Aussage endet nie als `FORMALLY_VERIFIED`.

### F-11.06 Externe Benchmarks miniF2F, ProofNet und PutnamBench

- Status: `todo` · Priorität: P1 · Meilenstein: M2, PutnamBench in M4
- Abhängigkeiten: F-11.03, F-00.07
- Quelle: ARCH §16.1
- Bearbeiter: offen · Nachweise: offen

Import mit Versionsstand und Lizenzprüfung. miniF2F dient dem Einstieg in Lean-Proof-Search, ProofNet der Autoformalisierung und dem Beweisen, PutnamBench komplexen Methoden und Agenten.

- [ ] Jeder Datensatz ist mit Version und Lizenz im Inventar (F-00.07) erfasst.
- [ ] Die Lean-Aussagen kompilieren mit der gepinnten Toolchain oder sind als inkompatibel markiert.

### F-11.07 Discover-and-Prove-Trennung

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-11.06
- Quelle: ARCH §16.1; Discover and Prove in ARCH §2.2
- Bearbeiter: offen · Nachweise: offen

Aufgaben, deren Antwort bereits in der formalen Aussage steht, werden markiert. Antwortentdeckung und formaler Beweis erhalten getrennte Ergebnisse.

- [ ] Benchmarkberichte zeigen beide Werte getrennt.

### F-11.08 Kontaminations- und Leakage-Kontrollen

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-11.03, F-03.08
- Quelle: ARCH §16.4, §21 (Train/Test-Leakage)
- Bearbeiter: offen · Nachweise: offen

Datensätze werden nach Problemfamilien und gegebenenfalls Veröffentlichungszeit aufgeteilt. Semantisch nahe Varianten werden über Fingerprints und `ProblemVariant` erkannt, damit Leakage zwischen Training und Test sichtbar bleibt.

- [ ] Eine Testaufgabe mit naher Variante im Trainingssatz wird gemeldet.
- [ ] Splits sind versioniert und unveränderlich.

### F-11.09 Benchmarkmetriken

- Status: `done` · Priorität: P0 · Meilenstein: M1, Ausbau M2 bis M5
- Abhängigkeiten: F-09.05
- Quelle: ARCH §16.3, §10.1; UI §12.2
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: compute M1 benchmark metrics at a fixed budget` auf `develop`. Am 2026-11-24 gelaufen: `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy` (strict), `uv run pytest` mit PostgreSQL (632 passed, 2 übersprungen) und ohne (611 passed, 23 übersprungen). `src/mathlab/benchmark_metrics.py` liefert für M1 Pass@k (erwartungstreuer Schätzer, per Hypothesis gegen die kombinatorische Definition geprüft), Success Rate, Time to Proof, CostPerProof und Fehler pro Klasse aus F-09.03. `sample_from_attempt` leitet Stichproben aus abgeschlossenen Versuchen (F-09.01) ab. `tests/test_benchmark_metrics.py` belegt, dass zensierte Laufzeiten getrennt ausgewiesen und nie als Erfolg oder Time to Proof gezählt werden, und dass ein Bericht nur Stichproben eines Budgets enthält und `compare_pass_at_k` Berichte mit verschiedenem Budget ablehnt. Annahmen: Ein abgeschlossener Versuch ohne Prüferurteil ist zensiert. Kosten sind nach ADR-0003 Modellaufrufe, Tokens und Laufzeit; nicht gemessene Tokens machen die Tokensumme unbekannt statt 0. Die übrigen Metriken aus ARCH §16.3 folgen mit ihren Features.

CostPerProof als gesamter Rechenaufwand geteilt durch die Zahl formal gelöster Probleme. Dazu Pass@k, Success Rate, Time to Proof, Proofs per Compute Hour, Verified Lemmas per Run, Search Depth, Premise Recall@k, Strategy Diversity, Counterexample Discovery Rate, Transfer Success, Semantic Formalization Accuracy, Explanation Quality und offene oder zensierte Laufzeiten. M1 liefert Pass@k, Success Rate, Time to Proof, CostPerProof und Fehler, die übrigen Metriken folgen mit ihren Features.

- [x] Zensierte Laufzeiten werden als solche markiert und nicht als Erfolg gezählt.
- [x] Pass@k wird nur bei gleichem Budget verglichen.

### F-11.10 Strategievergleich bei festem Budget

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-11.03, F-06.03
- Quelle: ARCH §19 (Phase 2, Akzeptanz), §16.4, §22 (Schritt 7)
- Bearbeiter: offen · Nachweise: offen

Unterschiedliche Strategien und Suchverfahren werden auf derselben Aufgabenmenge mit identischem Budget, identischer Toolchain und identischen Solverlimits verglichen.

- [ ] Abnahme M2: Ein Vergleichsbericht für mindestens drei Strategien mit festem Budget liegt vor.

### F-11.11 Ablationsstudien

- Status: `todo` · Priorität: P1 · Meilenstein: M4
- Abhängigkeiten: F-11.10, F-10.06
- Quelle: ARCH §16.4
- Bearbeiter: offen · Nachweise: offen

Ablationen ohne Graph, ohne Memory, ohne Critic, ohne RL, nur symbolisch, nur LLM und mit unterschiedlicher Strategiezuteilung.

- [ ] Jede der sieben Ablationen ist über Konfiguration auslösbar und wurde einmal ausgewertet.

### F-11.12 Seeds, Streuung und Konfidenzintervalle

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-11.03
- Quelle: ARCH §16.4 (letzter Punkt)
- Bearbeiter: offen · Nachweise: offen

Wiederholungen mit mehreren Seeds, statistische Streuung und Konfidenzintervalle in jedem Vergleichsbericht.

- [ ] Kein Vergleichsbericht ohne Seed-Anzahl und Konfidenzintervall.

### F-11.13 Forschungsnahe Benchmarks

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-11.06
- Quelle: ARCH §16.1 (TheoremBench, MathAdv, First Proof), §16.2 (Level 4 bis 6), §19 (Phase 6); ARCH §2.4
- Bearbeiter: offen · Nachweise: offen

TheoremBench für Hilfssatzabhängigkeiten, MathAdv für Robustheit gegenüber Umformulierungen und First Proof für forschungsnahe Mathematik. Dazu eigene Aufgaben der Level 4 bis 6.

- [ ] Jeder Datensatz ist importiert und mit Version erfasst.
- [ ] MathAdv-Ergebnisse werden nach Variante und Original getrennt berichtet.

### F-11.14 Evaluation Engine für Beweisvergleiche

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-08.10, F-09.05
- Quelle: ARCH §4.1 (Experiment/Evaluation Engine), §15.5 (Schritt 7), §7.4 (Schritt 2), §10.1 (Beweisqualität); ProofRank in ARCH §2.4
- Bearbeiter: offen · Nachweise: offen

Vergleicht mehrere Beweise derselben Aussage nach Korrektheit, Beweislänge, Rechenkosten, Methoden, Struktur und Wiederverwendbarkeit. Beweisqualität bleibt mehrdimensional und wird nicht zu einer Zahl verdichtet.

- [ ] Für die Odd-Sum-Aufgabe liegt ein Vergleich der gefundenen Beweise vor.
- [ ] Beweislänge wird nicht als Wahrheitskriterium verwendet (UI §12.2).
