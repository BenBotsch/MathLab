# E17 Inspector

- Status: `todo` · Meilenstein: M1, Ausbau M2 und M5
- Quellen: ARCH §14.3; UI §3.1, §7, §20 (Stufe 1), §21 (Epic UI-04)
- Abhängige Epics: E04, E14, E15, E16

## Ziel

Der rechte Inspector zeigt kontextsensitiv alle Details zum ausgewählten Beweisschritt, zur Hypothese oder zum Agenten, mit Provenienz, Verifikationsstatus und Crosslinks.

## Abgrenzung

Die Daten liefern E04, E09 und E13. Aktionen im Inspector lösen Kommandos aus E20 aus.

## Invarianten

Der Inspector zeigt für jeden Schritt Provenienz und Verifikationsstatus (UI §20, Kriterium 3). Er behauptet nie, interne Gedankenketten eines Modells live zu zeigen (UI §7.3). Sichtbar sind nur strukturierte Pläne, Modelloutputs, Werkzeugein- und ausgaben und formale Artefakte.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-17.01 | Aussage, Lean-Ziel und Methode | `todo` | P0 | M1 |
| F-17.02 | Proof State Diff | `todo` | P0 | M1 |
| F-17.03 | Lean-Code und Toollogs | `todo` | P0 | M1 |
| F-17.04 | Verifikations- und Axiomreport | `todo` | P0 | M1 |
| F-17.05 | Lemma-Provenienz und Crosslinks | `todo` | P0 | M1 |
| F-17.06 | Versionen, Ressourcen und Retries | `todo` | P1 | M1 |
| F-17.07 | Alternative Fortsetzungen und Methoden | `todo` | P1 | M2 |
| F-17.08 | Hypothesen-Inspector | `todo` | P1 | M2 |
| F-17.09 | Agenten-Inspector | `todo` | P1 | M1 |
| F-17.10 | Anzeige „Warum ist dieser Schritt gültig?“ | `todo` | P1 | M5 |

## Features

### F-17.01 Aussage, Lean-Ziel und Methode

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-16.06, F-14.02
- Quelle: UI §7.1 (Punkte 1 bis 3), §21 (Epic UI-04, LaTeX-Darstellung)
- Bearbeiter: offen · Nachweise: offen

Zielaussage als LaTeX über KaTeX, formale Lean-Aussage mit Hypothesen sowie Methode, Taktik und Parameter.

- [ ] LaTeX und Lean-Aussage stammen aus demselben Knoten und derselben Version.

### F-17.02 Proof State Diff

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-17.01, F-09.02
- Quelle: UI §7.1 (Punkt 4), §21 (Epic UI-04)
- Bearbeiter: offen · Nachweise: offen

Proof State vor und nach dem Schritt als Diff.

- [ ] Hinzugefügte und geschlossene Ziele sind im Diff gekennzeichnet.

### F-17.03 Lean-Code und Toollogs

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-17.01, F-14.06
- Quelle: UI §7.1 (Punkt 6), §19 (Monaco Editor), §21 (Epic UI-04)
- Bearbeiter: offen · Nachweise: offen

Lean-Code und Toollogs schreibgeschützt in einem Editor mit Syntaxhervorhebung, nachgeladen über Artefakt-IDs. Fehlermeldungen sind mit der Codezeile verknüpft.

- [ ] Große Logs werden erst bei Auswahl geladen.

### F-17.04 Verifikations- und Axiomreport

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-17.01, F-04.05
- Quelle: UI §7.1 (Punkt 6), §21 (Epic UI-04)
- Bearbeiter: offen · Nachweise: offen

Formale Verifikationsausgabe, verwendete Axiome und Hinweise auf `sorry` oder unerlaubte Axiome.

- [ ] Ein Schritt ohne Verifikationsartefakt zeigt den Status offen und keinen Haken.

### F-17.05 Lemma-Provenienz und Crosslinks

- Status: `todo` · Priorität: P0 · Meilenstein: M1, Wissensgraph-Links M2
- Abhängigkeiten: F-17.01, F-01.05
- Quelle: UI §7.1 (Punkte 5 und 10), §20 (Kriterium 3), §21 (Epic UI-04)
- Bearbeiter: offen · Nachweise: offen

Verwendete Lemmata mit Quelle, Version und Verifikationsstatus sowie Sprünge in Timeline und, ab M2, Wissensgraph.

- [ ] Jedes angezeigte Lemma hat eine Quelle oder ist als ohne Quelle markiert.

### F-17.06 Versionen, Ressourcen und Retries

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-17.01, F-09.02
- Quelle: UI §7.1 (Punkte 7 und 8)
- Bearbeiter: offen · Nachweise: offen

Agent, Modell und Toolversionen, verbrauchte Ressourcen und Anzahl lokaler Retries.

- [ ] Die Werte stimmen mit dem gespeicherten ProofAttempt überein.

### F-17.07 Alternative Fortsetzungen und Methoden

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-17.01, F-08.10
- Quelle: UI §7.1 (Punkt 9), §21 (Epic UI-04)
- Bearbeiter: offen · Nachweise: offen

Bekannte alternative Fortsetzungen und alternative Beweise des Ziels.

- [ ] Alternativen sind nach Verifikationsstatus getrennt.

### F-17.08 Hypothesen-Inspector

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-17.01, F-05.07
- Quelle: UI §7.2
- Bearbeiter: offen · Nachweise: offen

Ursprünglicher Wortlaut und formale Version, Definitionsbereiche und Voraussetzungen, experimentelle Evidenz und Fälle, Gegenbeispiele, fehlende Beweispflichten und verwandte Theoreme.

- [ ] Empirische Evidenz ist klar von Beweispflichten getrennt dargestellt.

### F-17.09 Agenten-Inspector

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-18.02
- Quelle: UI §7.3
- Bearbeiter: offen · Nachweise: offen

Rolle, Toolrechte, Modellversion, Auftrag, Verlauf von Subtasks und Toolaufrufen, verwendeter Kontext und abgerufene Lemmata, explizite Planungsartefakte und Begründungszusammenfassungen, technische Fehler und Retry-Historie.

- [ ] Die Ansicht ist mit „strukturierte Ausgaben“ beschriftet und nicht als Gedankenmitschnitt.

### F-17.10 Anzeige „Warum ist dieser Schritt gültig?“

- Status: `todo` · Priorität: P1 · Meilenstein: M5
- Abhängigkeiten: F-17.05, F-13.06
- Quelle: ARCH §14.3 (letzter Absatz)
- Bearbeiter: offen · Nachweise: offen

Aufklappbare Voraussetzungen und verwendete Lemmata eines Schritts bis zu Definitionen.

- [ ] Fehlende Belege werden als nicht verifiziert gezeigt.
