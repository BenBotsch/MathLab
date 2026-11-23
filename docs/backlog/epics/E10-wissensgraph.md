# E10 Wissensgraph und mathematisches Langzeitgedächtnis

- Status: `todo` · Meilenstein: M3, Vorstufe M2, Ausbau M6
- Quellen: ARCH §2.3, §4.1 (Knowledge Engine), §4.2, §6.1, §11, §17.1, §17.2, §18.4, §19 (Phase 3), §21, §22 (Schritt 8); UI §6.1, §6.2, §20 (Stufe 2)
- Abhängige Epics: E01, E02, E03, E04, E09

## Ziel

Verifizierte Lemmata, Theoreme, Methoden, Gegenbeispiele und Fehlversuche werden problemübergreifend gespeichert und wiederauffindbar gemacht. Jede Beziehung trägt Provenienz, Bedingungen und Vertrauensebene, damit Agenten nur belegtes Wissen als belegt verwenden.

## Abgrenzung

Die Darstellung liegt in E21 (F-21.01). Der Knowledge Agent liegt in F-07.11. Die Normalisierung von Ausdrücken liegt in F-03.07. Die Revalidierung bei Bibliothekswechsel liegt in F-04.09.

## Invarianten

Statistische Ähnlichkeit wird nie automatisch als mathematische Äquivalenz interpretiert (ARCH §11.2). Jeder Eintrag trägt `source_id`, `proof_artifact_id` und `verification_status` (ARCH §18.4). Ein Lemma wird nur mit definiertem Geltungsbereich und nachvollziehbarer Evidenz wiederverwendet (ARCH §4.2). Für den MVP genügt PostgreSQL für die Graphkanten (ARCH §17.2).

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-10.01 | Objektklassen und Speicherschema | `ready` | P0 | M2 |
| F-10.02 | Typisierte Relationen mit Kantenattributen | `todo` | P0 | M2 |
| F-10.03 | Aufnahme verifizierter Ergebnisse | `todo` | P0 | M2 |
| F-10.04 | Vertrauensebenen und Quarantäne | `todo` | P0 | M3 |
| F-10.05 | Exakte und strukturelle Suche | `todo` | P0 | M3 |
| F-10.06 | Hybride Retrieval-Pipeline | `todo` | P0 | M3 |
| F-10.07 | Positive Memory | `todo` | P1 | M3 |
| F-10.08 | Negative Memory | `todo` | P1 | M3 |
| F-10.09 | Problemübergreifende Wiederverwendung | `todo` | P0 | M3 |
| F-10.10 | Premise-Index für Mathlib | `todo` | P1 | M3 |
| F-10.11 | Äquivalenz und Ähnlichkeit trennen | `todo` | P1 | M3 |
| F-10.12 | Transfer Model | `todo` | P2 | M6 |

## Features

### F-10.01 Objektklassen und Speicherschema

- Status: `ready` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-01.02, F-02.03
- Quelle: ARCH §11.1, §17.2, §22 (Schritt 8); UI §6.1
- Bearbeiter: offen · Nachweise: offen

Die 15 Objektklassen aus ARCH §11.1: `Problem`, `FormalStatement`, `Definition`, `Theorem`, `Lemma`, `Equation`, `Expression`, `Proof`, `ProofMethod`, `Concept`, `Counterexample`, `Experiment`, `Model`, `Publication` und `AgentRun`. Die Knotentypen aus UI §6.1 sind darin enthalten. Speicherung als Graphprojektion in PostgreSQL, keine eigene Graphdatenbank im MVP.

- [ ] Alle 15 Klassen sind als Schema mit Migration angelegt.
- [ ] Eine separate Graphdatenbank wird nur über ein ADR mit Performancenachweis eingeführt.

### F-10.02 Typisierte Relationen mit Kantenattributen

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-10.01
- Quelle: ARCH §11.2, §18.4; UI §6.2
- Bearbeiter: offen · Nachweise: offen

Die zwölf Relationen `USES_THEOREM`, `DEPENDS_ON`, `IS_EQUIVALENT_TO`, `IMPLIES`, `GENERALIZES`, `IS_SPECIAL_CASE_OF`, `USES_PROOF_METHOD`, `HAS_COUNTEREXAMPLE`, `PROVEN_BY`, `SIMILAR_TO`, `DERIVED_FROM` und `REQUIRES_ASSUMPTION`. Jede Kante trägt Relationstyp, Richtung, Quelldokument oder Beweisartefakt, Bedingungen, Provenienz, Verifikationsstatus, Versionsstand und gegebenenfalls ein Ähnlichkeits- oder Konfidenzmaß.

- [ ] Eine Kante ohne Provenienz oder Verifikationsstatus wird abgelehnt.
- [ ] Jeder Eintrag hat `source_id`, `proof_artifact_id` und `verification_status`.

### F-10.03 Aufnahme verifizierter Ergebnisse

- Status: `todo` · Priorität: P0 · Meilenstein: M2
- Abhängigkeiten: F-10.02, F-04.07
- Quelle: ARCH §7.2 (Schritt 6), §7.4 (Schritt 3), §18.4, §22 (Schritt 8); UI §20 (Stufe 2, erstes Kriterium)
- Bearbeiter: offen · Nachweise: offen

Verifizierte Lemmata und Beziehungen aus einem Run werden über eine geprüfte API in den Graphen geschrieben, unabhängig davon, ob der Gesamtbeweis gelang. Erzeugt `knowledge.updated`.

- [ ] Ein verifiziertes Lemma ist zwischen Proof Graph und Wissensgraph über dieselbe ID auffindbar.
- [ ] Agenten können den Graphen nicht direkt beschreiben.

### F-10.04 Vertrauensebenen und Quarantäne

- Status: `todo` · Priorität: P0 · Meilenstein: M3
- Abhängigkeiten: F-10.02
- Quelle: ARCH §11.2 (drei Vertrauensebenen), §21 (selbstverstärkende falsche Memory); UI §6.2, §6.3
- Bearbeiter: offen · Nachweise: offen

Drei Ebenen: verifiziert oder abgeleitet, unverifiziert aber plausibel (agentische Hypothese), statistisch ähnlich. Neue unverifizierte Einträge liegen in Quarantäne, bis ein Validierungsworkflow sie bestätigt oder verwirft.

- [ ] Abfragen liefern die Vertrauensebene bei jedem Treffer mit.
- [ ] Einträge in Quarantäne werden nie als verifiziert ausgegeben (Test).

### F-10.05 Exakte und strukturelle Suche

- Status: `todo` · Priorität: P0 · Meilenstein: M3
- Abhängigkeiten: F-10.01, F-03.07
- Quelle: ARCH §11.3 (Schritt 1), §11.4, §3.1 (exakte AST-Suche)
- Bearbeiter: offen · Nachweise: offen

Suche nach Theoremnamen, Typen, Operatoren, Quantoren, AST-Mustern und Geltungsbereichen über normalisierte Fingerprints.

- [ ] Eine alpha-äquivalente Umbenennung findet dasselbe Lemma.

### F-10.06 Hybride Retrieval-Pipeline

- Status: `todo` · Priorität: P0 · Meilenstein: M3
- Abhängigkeiten: F-10.05, F-10.04
- Quelle: ARCH §11.3, §6.1 (Premise Retriever), §17.1 (pgvector), §19 (Phase 3)
- Bearbeiter: offen · Nachweise: offen

Die fünf Stufen aus ARCH §11.3 als Pipeline.

1. Exakt (F-10.05).
2. Semantisch über Embeddings in pgvector für natürliche Sprache, LaTeX und normalisierte Formalisierungen.
3. Graphbasiert über Dependency-Walks, Nachbarschaft und mehrstufige Lemma-Gruppen.
4. Reranking von Hilfssatz-Paketen nach Zielzustand, Voraussetzungen und Suchplan.
5. Validierung der Typen und Voraussetzungen gegen den aktuellen Beweiszustand vor der Verwendung.

- [ ] Jede Stufe ist einzeln abschaltbar, damit Ablationen möglich sind (F-11.11).
- [ ] Premise Recall@k wird mit Daten- und Abfrageversion gemessen (F-11.09).
- [ ] Ein Treffer, der Schritt 5 nicht besteht, wird nicht als verwendbar ausgegeben.

### F-10.07 Positive Memory

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-10.03
- Quelle: ARCH §11.5
- Bearbeiter: offen · Nachweise: offen

Speichert bewiesene Hilfssätze, erfolgreiche Strategien, nützliche Umformungen, wiederverwendbare Ideen und nachgewiesene Methodenübertragungen.

- [ ] Eine erfolgreiche Strategie ist mit Problemklasse und Budget abrufbar.

### F-10.08 Negative Memory

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-10.03, F-09.04
- Quelle: ARCH §11.5, §9.3, §19 (Phase 3, strukturierte Fehlversuchs-Memory)
- Bearbeiter: offen · Nachweise: offen

Speichert Gegenbeispiele, inkonsistente Voraussetzungen, fehlgeschlagene Methoden mit Kontext, teure Sackgassen und bekannte Verifikationslücken. Suchantworten zeigen neben Erfolgen auch bekannte Risiken und nicht erfüllte Voraussetzungen.

- [ ] Eine Retrieval-Antwort zu einem Ziel mit bekannter Sackgasse enthält den Warnhinweis.
- [ ] Negative Einträge sind nach Kontext gefiltert (F-09.04).

### F-10.09 Problemübergreifende Wiederverwendung

- Status: `todo` · Priorität: P0 · Meilenstein: M3
- Abhängigkeiten: F-10.06, F-07.11
- Quelle: ARCH §19 (Phase 3, Akzeptanz), §1.1 (Fähigkeit 6); UI §12.2 (Knowledge Reuse)
- Bearbeiter: offen · Nachweise: offen

Ein Lemma aus einem früheren Run wird bei einem zweiten Problem gefunden und angewendet. Knowledge Reuse zählt nur echte Wiederverwendung im verifizierten Beweis.

- [ ] Abnahme M3: Ein nachgewiesenes Lemma wird bei einem zweiten Problem wiedergefunden und erfolgreich mit dokumentierter Provenienz angewendet.
- [ ] Der Zähler für Wiederverwendung steigt nur bei Verwendung in einem verifizierten Beweis.

### F-10.10 Premise-Index für Mathlib

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-10.05, F-04.01
- Quelle: ARCH §11.3; LeanSearch v2, LeanGraphSearch, TheoremGraph und DAPS in ARCH §2.3
- Bearbeiter: offen · Nachweise: offen

Mathlib-Theoreme der gepinnten Version werden mit Namen, Typ und Abhängigkeiten indexiert, damit der Premise Retriever erlaubte Hilfssätze mit exakter Bibliotheksreferenz liefert.

- [ ] Jeder Treffer trägt eine exakte Mathlib-Referenz und Version (ARCH §21, halluzinierte Lemmata).
- [ ] Ein Versionswechsel baut den Index neu auf.

### F-10.11 Äquivalenz und Ähnlichkeit trennen

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-10.02, F-03.07
- Quelle: ARCH §11.2, §11.4 (letzter Punkt); SemantEq in ARCH §2.3; UI §6.2
- Bearbeiter: offen · Nachweise: offen

`IS_EQUIVALENT_TO` wird nur mit Regelanwendung oder Beweis gesetzt. Embedding- oder Strukturähnlichkeit erzeugt höchstens `SIMILAR_TO` auf der dritten Vertrauensebene.

- [ ] Zwei ähnliche, nicht äquivalente Theoreme erhalten keine Äquivalenzkante (Test aus F-11.05).

### F-10.12 Transfer Model

- Status: `todo` · Priorität: P2 · Meilenstein: M6
- Abhängigkeiten: F-10.06, F-12.01
- Quelle: ARCH §6.1 (Transfer Model), §19 (Phase 6, Cross-Domain-Methodentransfer), §20 (Beitrag B)
- Bearbeiter: offen · Nachweise: offen

Methodentransfer zwischen Problemklassen. Erste Implementierung über Graph-Retrieval, später GNN oder Encoder.

- [ ] Transfer Success wird nach Problemfamilien getrennt gemessen, mit Leakage-Prüfung (F-11.08).
- [ ] Negative Transferfälle werden gezählt.
