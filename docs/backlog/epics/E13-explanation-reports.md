# E13 Explanation Engine und Research Reports

- Status: `todo` · Meilenstein: M5, Vorstufe M2
- Quellen: ARCH §4.1 (Explanation Engine), §6.1, §7.4 (Schritt 6), §14.1 bis §14.3, §16.3, §19 (Phase 5); UI §7.1, §13.4
- Abhängige Epics: E04, E09, E10

## Ziel

Formal geprüfte Beweise werden in verständliche, belegte Erklärungen und versionierte Berichte übersetzt. Jede zusätzliche Behauptung ist auf verifizierte Aussagen zurückgeführt oder als nicht bewiesen gekennzeichnet.

## Abgrenzung

Die Anzeige im Inspector liegt in E17, die Report-Seite der UI in F-21.08. Die Visualisierungsbibliotheken der Live-Ansichten liegen in E15 und E21.

## Invarianten

Eine Erklärung ist nie Grundlage für den Status `FORMALLY_VERIFIED`. Natürlichsprachige Texte werden nicht als Beweis ausgegeben. Berichte sind versioniert und unveränderlich.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-13.01 | Extraktion akzeptierter Schritte und Konzepte | `todo` | P1 | M2 |
| F-13.02 | Explanation Agent mit Erklärungstiefen | `todo` | P1 | M5 |
| F-13.03 | Belegpflicht für Behauptungen | `todo` | P0 | M5 |
| F-13.04 | Beweisbericht | `todo` | P1 | M2 |
| F-13.05 | Exporte Markdown, LaTeX, PDF und Lean | `todo` | P1 | M5 |
| F-13.06 | Abfrage „Warum ist dieser Schritt gültig?“ | `todo` | P1 | M5 |
| F-13.07 | Illustrationen, Diagramme und Animationen | `todo` | P2 | M5 |
| F-13.08 | Graphviz-Export | `ready` | P2 | M5 |
| F-13.09 | Lean Blueprint und ProofWidgets4 | `todo` | P2 | M5 |
| F-13.10 | Explanation Viewer | `todo` | P1 | M5 |
| F-13.11 | Bewertung der Erklärungsqualität | `todo` | P2 | M5 |

## Features

### F-13.01 Extraktion akzeptierter Schritte und Konzepte

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.04, F-10.01
- Quelle: ARCH §14.3 (Schritte 1 und 2)
- Bearbeiter: offen · Nachweise: offen

Formal akzeptierte Schritte mit ihren Abhängigkeiten sowie die relevanten Definitionen und Konzepte werden aus dem Beweisartefakt extrahiert.

- [ ] Für den Odd-Sum-Beweis liegt eine Schrittliste mit Abhängigkeiten vor.

### F-13.02 Explanation Agent mit Erklärungstiefen

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-13.01, F-07.03
- Quelle: ARCH §14.3 (Schritte 3 und 4), §6.1 (Explanation Model), §6.2
- Bearbeiter: offen · Nachweise: offen

Überträgt den Beweis in natürliche Sprache, mit getrennten Tiefen für Einsteiger und Experten.

- [ ] Beide Tiefen werden für die Golden-Aufgaben erzeugt und versioniert gespeichert.

### F-13.03 Belegpflicht für Behauptungen

- Status: `todo` · Priorität: P0 · Meilenstein: M5
- Abhängigkeiten: F-13.02
- Quelle: ARCH §14.3 (Schritt 6), §19 (Phase 5, zitierbare Erklärungen)
- Bearbeiter: offen · Nachweise: offen

Jede mathematische Aussage einer Erklärung verweist auf ein verifiziertes Artefakt oder ist sichtbar als nicht bewiesen markiert.

- [ ] Ein Test findet keine Aussage ohne Beleg oder Markierung.

### F-13.04 Beweisbericht

- Status: `todo` · Priorität: P1 · Meilenstein: M2, vollständig M5
- Abhängigkeiten: F-13.01, F-09.05
- Quelle: ARCH §7.4 (Schritt 6), §19 (Phase 5, Akzeptanz); UI §13.4
- Bearbeiter: offen · Nachweise: offen

Ein versionierter Bericht mit den acht Inhalten aus UI §13.4: ursprüngliche Problemdefinition, endgültige formale Zielaussage, verwendete Definitionen und Beweismethoden, Prüfstatus und Axiomreport, Erklärungen, Diagramme und Simulationen, referenzierte Quellen sowie durchgeführte Versuche mit Ergebnisvergleich. M2 liefert die Inhalte ohne Erklärungen und Diagramme.

- [ ] Abnahme M5: Herkunft, Hilfssätze, Alternativen, Laufzeiten und eine lesbare Herleitung sind aus dem Bericht abrufbar.

### F-13.05 Exporte Markdown, LaTeX, PDF und Lean

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-13.04
- Quelle: UI §13.4; ARCH §19 (Phase 5)
- Bearbeiter: offen · Nachweise: offen

- [ ] Alle vier Formate werden aus derselben Berichtsversion erzeugt.
- [ ] Der Lean-Export kompiliert mit der gepinnten Toolchain.

### F-13.06 Abfrage „Warum ist dieser Schritt gültig?“

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-13.01
- Quelle: ARCH §14.3 (letzter Absatz); UI §7.1
- Bearbeiter: offen · Nachweise: offen

API, die zu einem Beweisschritt die notwendigen Voraussetzungen und verwendeten Lemmata liefert. Die Anzeige liegt in F-17.10.

- [ ] Die Antwort enthält nur verifizierte Abhängigkeiten oder markiert fehlende.

### F-13.07 Illustrationen, Diagramme und Animationen

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-13.02, F-05.04
- Quelle: ARCH §14.3 (Schritt 5), §14.2 (Plotly, Manim), §15.4
- Bearbeiter: offen · Nachweise: offen

Geometrische Illustrationen, Diagramme oder Simulationen ergänzen die Erklärung, zum Beispiel die Quadratzerlegung aus ARCH §15.4 als Manim-Animation.

- [ ] Jede Illustration ist als Veranschaulichung und nicht als Beweis gekennzeichnet.

### F-13.08 Graphviz-Export

- Status: `ready` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-08.02
- Quelle: ARCH §14.2
- Bearbeiter: offen · Nachweise: offen

Statischer Export von Proof-Bäumen und Abhängigkeitsgraphen.

- [ ] Ein Proof Graph wird als SVG mit Statuskennzeichnung exportiert.

### F-13.09 Lean Blueprint und ProofWidgets4

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-13.01
- Quelle: ARCH §14.2
- Bearbeiter: offen · Nachweise: offen

Verknüpfung des formalen Projekts mit informeller Beweisplanung über Lean Blueprint sowie interaktive Visualisierungen in Lean über ProofWidgets4.

- [ ] Ein Blueprint für ein mehrstufiges Problem wird erzeugt und verlinkt.

### F-13.10 Explanation Viewer

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-13.03, F-15.01
- Quelle: ARCH §14.1 (Explanation Viewer)
- Bearbeiter: offen · Nachweise: offen

Ansicht für Schritt-für-Schritt-Erklärungen mit aufklappbaren Belegen und KaTeX-Darstellung.

- [ ] Jeder Erklärungsschritt verlinkt auf den zugehörigen Knoten im Proof Graph.

### F-13.11 Bewertung der Erklärungsqualität

- Status: `todo` · Priorität: P2 · Meilenstein: M5
- Abhängigkeiten: F-13.02
- Quelle: ARCH §16.3 (Explanation Quality), §10.1 (Verständlichkeit)
- Bearbeiter: offen · Nachweise: offen

Ein dokumentiertes Bewertungsverfahren, zum Beispiel Rubrik mit menschlicher Stichprobe. Die Metrik wird getrennt von der Korrektheit berichtet.

- [ ] Das Verfahren ist dokumentiert und auf der Golden Suite einmal angewendet.
