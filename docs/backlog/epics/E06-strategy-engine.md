# E06 Strategy Engine und Beweismethodenkatalog

- Status: `todo` · Meilenstein: M2, Ausbau M3 und M4
- Quellen: ARCH §4.1, §5, §6.1, §7.2, §19 (Phase 2), §22
- Abhängige Epics: E01, E03, E09

## Ziel

Beweismethoden sind als maschinenlesbare, versionierte Definitionen hinterlegt, mit Voraussetzungen, Strategie, Werkzeugen, typischen Fehlern und Erfahrungsstatistik. Die Strategy Engine wählt auf dieser Grundlage Methoden aus, erst regelbasiert und später lernend.

## Abgrenzung

Ausführung und Suche liegen in E07 und E08. Lernende Auswahlmodelle liegen in E12.

## Invarianten

Eine Methode wird nur angewendet, wenn ihre Voraussetzungen geprüft sind. Statistiken entstehen ausschließlich aus gespeicherten ProofAttempts.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-06.01 | Schema für Methodendefinitionen | `todo` | P0 | M2 |
| F-06.02 | Methodenregistry | `todo` | P0 | M2 |
| F-06.03 | Drei ausführbare Methodenstrategien | `todo` | P0 | M2 |
| F-06.04 | Vollständiger Methodenkatalog | `todo` | P1 | M3 |
| F-06.05 | Erfahrungsstatistik pro Methode | `todo` | P1 | M2 |
| F-06.06 | Methodenauswahl und Strategy Policy | `todo` | P1 | M2 |

## Features

### F-06.01 Schema für Methodendefinitionen

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-01.02
- Quelle: ARCH §5.2
- Bearbeiter: offen · Nachweise: offen

YAML-Schema für `ProofMethod` mit den Feldern aus dem Beispiel in ARCH §5.2: `id`, `version`, `category`, `applicable_to`, `preconditions`, `strategy`, `tools`, `failure_types` und `feedback`.

Im Beispiel `proof.induction.natural_numbers` (Version 1.0, Kategorie `induction`) gilt die Methode für allquantifizierte Aussagen, natürlichzahlige Parameter und rekursive Strukturen. Vorbedingungen sind eine identifizierte Induktionsvariable und eine fundierte Ordnung. Die Strategie besteht aus Induktionsanfang, Induktionsannahme, Aufbau des Nachfolgerziels und Induktionsschritt. Werkzeuge sind `lean4`, `sympy` und `lemma_retrieval`. Die Fehlertypen unterscheiden gescheiterten Anfang, unzureichende Annahme und gescheiterten Schritt. Als Rückmeldung liefert die Methode verifizierte Teilziele, offene Verpflichtungen, Beweistiefe und Rechenkosten.

- [ ] Das Beispiel „Vollständige Induktion“ aus ARCH §5.2 validiert gegen das Schema.
- [ ] Ungültige Definitionen werden mit Fehlermeldung abgelehnt.

Referenzbeispiel aus ARCH §5.2, unverändert zitiert. Bei Abweichung gilt die Quelle.

```yaml
method:
  id: proof.induction.natural_numbers
  version: 1.0
  category: induction
  applicable_to:
    - universally_quantified_statements
    - natural_number_parameters
    - recursive_structures
  preconditions:
    - induction_variable_identified
    - well_founded_order_available
  strategy:
    - prove_base_case
    - assume_induction_hypothesis
    - construct_successor_goal
    - prove_induction_step
  tools:
    - lean4
    - sympy
    - lemma_retrieval
  failure_types:
    - base_case_failed
    - induction_hypothesis_insufficient
    - induction_step_failed
  feedback:
    - verified_subgoals
    - remaining_obligations
    - proof_depth
    - computational_cost
```

### F-06.02 Methodenregistry

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-06.01
- Quelle: ARCH §5.2, §4.1
- Bearbeiter: offen · Nachweise: offen

Laden, Versionieren und Abfragen von Methoden nach Kategorie, Anwendbarkeit und Voraussetzung.

- [ ] Abfrage nach Kategorie liefert die passenden Methoden in stabiler Reihenfolge.
- [ ] Eine geänderte Methode erhält eine neue Version, alte Attempts verweisen weiter auf die alte.

### F-06.03 Drei ausführbare Methodenstrategien

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-06.02, F-07.07
- Quelle: ARCH §19 (Phase 2, „mindestens drei unterschiedliche Methodenstrategien“), §22 (Schritt 7)
- Bearbeiter: offen · Nachweise: offen

Drei Methoden werden als ausführbare Strategien mit Lean-Taktiken umgesetzt. Die Quelle legt die drei Methoden nicht fest. Vorschlag des Backlogs ist vollständige Induktion, algebraische Umformung und Widerspruchsbeweis, weil die ersten beiden das Referenzbeispiel aus ARCH §15 abdecken.

- [ ] Die Auswahl der drei Methoden ist vor Beginn bestätigt oder geändert.
- [ ] Jede der drei Methoden löst mindestens eine Golden-Aufgabe.
- [ ] Die drei Strategien werden bei festem Budget verglichen (F-11.10).

### F-06.04 Vollständiger Methodenkatalog

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-06.03
- Quelle: ARCH §5.1
- Bearbeiter: offen · Nachweise: offen

Alle 23 Methoden der Tabelle in ARCH §5.1 als Definition: Direkter Beweis, Widerspruch, Kontraposition, Vollständige Induktion, Strukturelle Induktion, Fallunterscheidung, Konstruktiver Existenzbeweis, Eindeutigkeit, Extremalprinzip, Invarianten, Monovarianten, Bijektion, Schubfachprinzip, Symmetrie, Ungleichungen, Algebraische Umformung, Geometrischer Beweis, Probabilistische Methode, Erzeugende Funktionen, Lineare Algebra, Reduktion, Intervallbeweis und Exhaustive Suche.

Die in ARCH §5.1 genannten weiteren Spezialmethoden folgen als zweite Gruppe: Kompaktheit, Fixpunktsätze, Diagonalisierung, analytische Fortsetzung, Gröbnerbasen, algebraische Geometrie, Inversionssätze, Darstellungen und Spektralmethoden.

- [ ] Jede der 23 Tabellenmethoden hat eine validierte Definition.
- [ ] Mindestens zehn Methoden sind ausführbar und mit Testaufgabe belegt.
- [ ] Die Spezialmethoden sind mindestens als Definition mit Status „nicht ausführbar“ erfasst.

### F-06.05 Erfahrungsstatistik pro Methode

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-06.02, F-09.02
- Quelle: ARCH §5.2
- Bearbeiter: offen · Nachweise: offen

Statistik pro Methode mit den Feldern aus ARCH §5.2: Anwendungsfälle, Geltungsbedingungen, Erfolg nach Problemklasse, durchschnittlicher Suchaufwand, häufige Fehler, hilfreiche Kombinationen und bevorzugte Modellkonfigurationen.

- [ ] Die Statistik wird aus Ereignissen rekonstruierbar berechnet.
- [ ] Jedes Feld ist nach Problemklasse abfragbar.

### F-06.06 Methodenauswahl und Strategy Policy

- Status: `todo` · Priorität: P1 · Meilenstein: M2, Ausbau M4
- Abhängigkeiten: F-06.05, F-03.06
- Quelle: ARCH §5.2, §6.1 (Strategy Policy als Contextual Bandit oder RL), §7.2 (Schritt 1)
- Bearbeiter: offen · Nachweise: offen

In M2 regelbasiert nach Klassifikation, Voraussetzungen und Statistik. In M4 als Contextual Bandit oder RL-Policy (F-12.03). Die Auswahl wird mit Begründung und Alternativen als `strategy.selected` gespeichert.

- [ ] Jede Auswahl ist mit Begründung und Alternativen gespeichert.
- [ ] Die gelernte Variante schlägt die Regelvariante auf einem festen Satz bei gleichem Budget oder wird verworfen (M4).
