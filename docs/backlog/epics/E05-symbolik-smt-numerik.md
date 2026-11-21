# E05 Symbolik, SMT, Numerik und Widerlegung

- Status: `todo` · Meilenstein: M1, Ausbau M2, M5 und M6
- Quellen: ARCH §4.1, §7.5, §12, §13.2, §17.1
- Abhängige Epics: E01, E02, E04, E24

## Ziel

Symbolische Rechnung, SMT-Solver und numerische Experimente liefern Kandidaten, Gegenbeispiele und Evidenz. Ihre Ergebnisse tragen die passende Erkenntnisstufe und werden erst nach Rekonstruktion in Lean formal gültig (F-04.10).

## Abgrenzung

Die Oberflächen für Symbolic und Simulation Workspace liegen in E21. Die Rekonstruktion in Lean liegt in E04. Die Contracts `SymbolicEngine` und `SimulationEngine` aus F-01.04 sind eine Erweiterung der in ARCH §18.2 genannten Schnittstellen.

## Invarianten

Numerische Evidenz ist kein Beweis und hebt eine Aussage höchstens auf `NUMERICALLY_SUPPORTED`. Jeder numerische Lauf speichert Seed, Präzision, Toolversion und Parameter. Experimente können eine Vermutung motivieren, der allgemeine Satz wird separat bewiesen (ARCH §12.2).

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-05.01 | SymPy-Adapter | `todo` | P0 | M1 |
| F-05.02 | Symbolische Schrittpipeline | `todo` | P0 | M1 |
| F-05.03 | SMT-Adapter für Z3 und cvc5 | `todo` | P1 | M2 |
| F-05.04 | Simulationsworkflow mit Seed und Präzision | `todo` | P1 | M2 |
| F-05.05 | Parameterstudien | `todo` | P1 | M2 |
| F-05.06 | Workflow E Widerlegungen | `todo` | P1 | M2 |
| F-05.07 | Gegenbeispiel-Objekt | `todo` | P0 | M1 |
| F-05.08 | SageMath-Adapter | `todo` | P2 | M5 |
| F-05.09 | ATP-Adapter für Vampire | `todo` | P2 | M6 |

## Features

### F-05.01 SymPy-Adapter

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.04, F-24.01
- Quelle: ARCH §12.1 (Standard-CAS im MVP), §17.1
- Bearbeiter: offen · Nachweise: offen

Implementiert den `SymbolicEngine`-Contract für Vereinfachung, Umformung, Gleichungslösen, Summen und Reihen. Läuft mit Zeitlimit in der Sandbox.

- [ ] Die Identität aus ARCH §15 (Summe der ersten n ungeraden Zahlen gleich n²) wird symbolisch bestätigt.
- [ ] Zeitüberschreitung liefert einen typisierten Fehler.

### F-05.02 Symbolische Schrittpipeline

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-05.01, F-01.01
- Quelle: ARCH §12.1, §13.2; UI §11.1
- Bearbeiter: offen · Nachweise: offen

Symbolische Ergebnisse werden als Ereignis `symbolic.calculation.completed` mit Eingabe, Ausgabe, Zwischenergebnissen, Transformationsquelle und Version gespeichert und erhalten die Stufe `SYMBOLICALLY_DERIVED`.

- [ ] Kein symbolisches Ergebnis erreicht ohne F-04.10 die Stufe `FORMALLY_VERIFIED`.
- [ ] Voraussetzungen und Definitionsbereiche der Variablen werden mitgespeichert.

### F-05.03 SMT-Adapter für Z3 und cvc5

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-01.04, F-24.01
- Quelle: ARCH §12.1, §7.5 (Schritt 3), §12.3
- Bearbeiter: offen · Nachweise: offen

Z3 dient der Modell- und Gegenbeispielsuche, cvc5 ist alternatives Backend mit Proof-Produktion. Ergebnisse `sat`, `unsat` und `unknown` werden getrennt geführt, Modelle bei `sat` als Gegenbeispielkandidat gespeichert.

- [ ] `unknown` wird nie als Bestätigung gewertet.
- [ ] Ein `sat`-Modell erzeugt einen Gegenbeispielkandidaten (F-05.07).

### F-05.04 Simulationsworkflow mit Seed und Präzision

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-01.04, F-02.07
- Quelle: ARCH §12.2, §12.1 (NumPy, SciPy); UI §11.2
- Bearbeiter: offen · Nachweise: offen

Implementiert den `SimulationEngine`-Contract und die sechs Schritte aus ARCH §12.2.

1. Parameter und Geltungsbereiche definieren.
2. Numerische Experimente mit fixiertem Seed und Präzision ausführen.
3. Ausreißer, Grenzwerte und potenzielle Gegenbeispiele identifizieren.
4. Vermutungen formulieren und symbolische Kandidaten herleiten.
5. Formale Verifikation versuchen.
6. Ergebnisse als experimentell, symbolisch oder formal geprüft klassifizieren.

Jeder Lauf ist ein `SimulationRun` mit Seed, Präzision, Toleranz, Parametern, Toolversion, erzeugender Modellversion und Ergebnisartefakt.

- [ ] Wiederholung mit gleichem Seed liefert identische Ergebnisse.
- [ ] Ereignis `simulation.sample.received` wird für Zwischenergebnisse erzeugt.
- [ ] Jedes Ergebnis trägt eine der drei Klassen aus Schritt 6.

### F-05.05 Parameterstudien

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-05.04
- Quelle: ARCH §12.2 (Beispiel x³−αx+1), §3.1; UI §11.3
- Bearbeiter: offen · Nachweise: offen

Systematische Variation von Parametern mit Erkennung von Nullstellenanzahl, kritischen Werten, Vorzeichenwechseln und Parameterbereichen. Aus Befunden entstehen Hypothesen mit Stufe `NUMERICALLY_SUPPORTED`.

- [ ] Für x³−αx+1 wird der Übergang der reellen Nullstellenanzahl bei α = 3/∛4 numerisch gefunden und als Hypothese gespeichert.
- [ ] Die Hypothese verweist auf die erzeugenden SimulationRuns.

### F-05.06 Workflow E Widerlegungen

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-05.03, F-05.04, F-05.07
- Quelle: ARCH §7.5, §12.3
- Bearbeiter: offen · Nachweise: offen

Die fünf Schritte aus ARCH §7.5 als ausführbarer Workflow.

1. Vermutung formalisieren und Definitionsbereiche prüfen.
2. Numerische Spezialfälle, Grenzfälle und Zufallsfälle testen.
3. Solver für Erfüllbarkeit und Gegenbeispiele einsetzen.
4. Ein gefundenes Gegenbeispiel exakt nachvollziehen und verifizieren.
5. Aussage als `REFUTED` markieren und falls sinnvoll neue eingeschränkte Vermutungen aufstellen.

- [ ] Die Aussage x² > x für alle x > 0 wird durch x = 0,5 widerlegt, als `REFUTED` markiert und die eingeschränkte Behauptung für x > 1 als neue Vermutung angelegt (ARCH §12.3).
- [ ] Ohne exakte Nachprüfung in Schritt 4 bleibt der Kandidat unbestätigt.

### F-05.07 Gegenbeispiel-Objekt

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02
- Quelle: ARCH §7.5, §12.3, §18.1 (Counterexample)
- Bearbeiter: offen · Nachweise: offen

`Counterexample` mit Aussage, Belegung, Herkunft, Prüfstatus und Artefakt. Erzeugt das Ereignis `counterexample.found`.

- [ ] Ein Gegenbeispiel ist mit Aussage, Herkunft und Prüfstatus abrufbar.

### F-05.08 SageMath-Adapter

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-05.01
- Quelle: ARCH §12.1, §17.1
- Bearbeiter: offen · Nachweise: offen

Adapter für erweiterte Fachdomänen wie Algebra und Zahlentheorie über denselben Contract.

- [ ] Ein zahlentheoretischer Testfall wird über den Adapter berechnet.

### F-05.09 ATP-Adapter für Vampire

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-01.04, F-24.01
- Quelle: ARCH §12.1
- Bearbeiter: offen · Nachweise: offen

Forschungsadapter für prädikatenlogische Teilziele. Gefundene Beweise dienen als Hinweis für die Lean-Rekonstruktion.

- [ ] Ein prädikatenlogisches Teilziel wird gelöst und der Beweis als Artefakt gespeichert.
