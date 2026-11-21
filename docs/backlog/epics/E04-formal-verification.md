# E04 Formal Verification Engine

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §4.1, §7.3, §13, §17.1, §18.4, §22 (Schritt 1)
- Abhängige Epics: E00, E01, E02, E24

## Ziel

Lean 4 mit Mathlib ist der Wahrheitsanker des Systems. Diese Engine prüft ganze Beweise und einzelne Beweispflichten in einer isolierten Umgebung, kontrolliert Axiome und `sorry`, gleicht das bewiesene Ziel mit dem Ziel-Hash ab und archiviert jedes Ergebnis als Artefakt.

## Abgrenzung

Die Erzeugung von Beweisen liegt in E07 und E08. Die Treue der Formalisierung zur Originalaufgabe prüft E03.

## Invarianten

Nur diese Engine erzeugt `VerificationResult` mit Status `VERIFIED`. Ist sie nicht erreichbar, bleibt der Status offen und wird nie als gültig angenommen.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-04.01 | Lean 4 und Mathlib einrichten | `todo` | P0 | M1 |
| F-04.02 | Lean-Interaktionsadapter | `todo` | P0 | M1 |
| F-04.03 | Isolierte Beweisprüfung | `todo` | P0 | M1 |
| F-04.04 | Zielabgleich | `todo` | P0 | M1 |
| F-04.05 | Axiomreport und `sorry`-Prüfung | `todo` | P0 | M1 |
| F-04.06 | Unabhängige Nachprüfung | `todo` | P1 | M1 |
| F-04.07 | Archiv der Verifikationsartefakte | `todo` | P0 | M1 |
| F-04.08 | Prüfung einzelner Beweispflichten | `todo` | P0 | M1 |
| F-04.09 | Verifikations-Cache und Revalidierung | `todo` | P1 | M2 |
| F-04.10 | Rekonstruktion externer Ergebnisse | `todo` | P1 | M2 |

## Features

### F-04.01 Lean 4 und Mathlib einrichten

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.03, F-00.04
- Quelle: ARCH §17.1, §22 (Schritt 1), §7.3 (Schritt 3)
- Bearbeiter: offen · Nachweise: offen

Lean-Projekt mit gepinnter Toolchain und Mathlib-Version, vorkompiliertem Cache und einem Beispielbeweis.

- [ ] Der Beispielbeweis aus ARCH §15 (Summe ungerader Zahlen) kompiliert im Container.
- [ ] Lean- und Mathlib-Version erscheinen im Environment-Fingerprint.

### F-04.02 Lean-Interaktionsadapter

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.01, F-01.04, F-00.01 (OD-02)
- Quelle: ARCH §17.1 (LeanDojo, Pantograph); LeanDojo in ARCH §2.1
- Bearbeiter: offen · Nachweise: offen

Python-Adapter, der Proof States liest, Taktiken ausführt und Fehler strukturiert zurückgibt. Implementiert den `VerificationEngine`-Contract und die für die Suche nötigen Zustandsoperationen.

- [ ] Ein Ziel kann geöffnet, eine Taktik angewendet und der neue Proof State gelesen werden.
- [ ] Lean-Fehler werden auf den Fehlerkatalog (F-09.03) abgebildet.
- [ ] Timeouts und Abbruch funktionieren.

### F-04.03 Isolierte Beweisprüfung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.02, F-24.01
- Quelle: ARCH §7.3 (Schritt 1), §21 (gefährlicher generierter Code)
- Bearbeiter: offen · Nachweise: offen

Vollständige Lean-Quelle aus Zielaussage und Beweis wird in einer Sandbox ohne Netz und mit Ressourcenlimits geprüft.

- [ ] Ein Beweis mit Endlosschleife wird nach Zeitlimit mit `RESOURCE_EXHAUSTION` beendet.
- [ ] Die Prüfung hat keinen Netzzugriff.

### F-04.04 Zielabgleich

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.03, F-01.03
- Quelle: ARCH §7.3 (Schritt 5), §13.1, §13.2, §18.4
- Bearbeiter: offen · Nachweise: offen

Das bewiesene Theorem muss exakt der Zielaussage mit dem bestätigten Hash entsprechen oder einer kontrolliert äquivalenten Form mit eigenem Nachweis.

- [ ] Ein Beweis eines abgeschwächten Ziels wird abgelehnt.
- [ ] Ein Beweis mit veränderter Zielaussage wird abgelehnt, auch wenn er kompiliert.

### F-04.05 Axiomreport und `sorry`-Prüfung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.03
- Quelle: ARCH §7.3 (Schritt 2), §13.2, §21
- Bearbeiter: offen · Nachweise: offen

Für jeden geprüften Beweis entsteht ein Report der verwendeten Axiome. `sorry`, `sorryAx`, benutzerdefinierte Axiome und andere unzulässige Vertrauenskonstrukte führen zur Ablehnung. Mechanismen mit zusätzlichen Vertrauensannahmen werden im Report ausgewiesen (ARCH §13.2).

- [ ] Ein Beweis mit `sorry` wird abgelehnt.
- [ ] Ein Beweis mit eigenem `axiom` wird abgelehnt.
- [ ] Die erlaubten Standardaxiome sind konfiguriert und dokumentiert.

### F-04.06 Unabhängige Nachprüfung

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-04.05
- Quelle: ARCH §7.3 (Schritt 4), §13.2; Lean-Dokumentation „Validating a Lean Proof“
- Bearbeiter: offen · Nachweise: offen

Verifizierte Beweise werden zusätzlich mit `lean4checker --fresh` oder dem jeweils dokumentierten Mechanismus erneut geprüft. Bei hohem Schutzbedarf ist ein unabhängiger Checker vorgesehen. Die Werkzeugwahl erfolgt gemäß der aktuellen Lean-Dokumentation.

- [ ] Die Nachprüfung läuft für jeden als `VERIFIED` markierten Beweis und ist im Artefakt vermerkt.

### F-04.07 Archiv der Verifikationsartefakte

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.05, F-02.07
- Quelle: ARCH §7.3 (Schritt 6)
- Bearbeiter: offen · Nachweise: offen

Beweisquelle, Axiomreport, Log und Fingerprints werden als Artefakte gespeichert und mit dem `VerificationResult` verknüpft.

- [ ] Jedes `VerificationResult` verweist auf vollständige Artefakte.
- [ ] Aus den Artefakten lässt sich die Prüfung reproduzieren.

### F-04.08 Prüfung einzelner Beweispflichten

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.04
- Quelle: ARCH §3.1 (Verifikation einzelner Lemmata), §7.2 (Schritt 6); UI §20 (Kriterium 2)
- Bearbeiter: offen · Nachweise: offen

Teilziele und Lemmata werden unabhängig vom Gesamterfolg geprüft. Ergebnis ist ein Ereignis `proof.step.verified`, `lemma.verified` oder `proof.step.rejected`.

- [ ] Ein verifiziertes Teilziel erzeugt das Ereignis mit Verweis auf das Artefakt.
- [ ] Ein Lemma kann `VERIFIED` sein, während das Hauptziel offen bleibt.

### F-04.09 Verifikations-Cache und Revalidierung

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.07
- Quelle: ARCH §18.4
- Bearbeiter: offen · Nachweise: offen

Cache über den Hash von Aussage, Beweis, Toolchain und Abhängigkeiten. Wechselt die Mathlib-Version, werden abhängige Zertifikate erneut geprüft.

- [ ] Identische Prüfanfragen werden aus dem Cache beantwortet.
- [ ] Nach einem Versionswechsel sind betroffene Ergebnisse als „zu revalidieren“ markiert.

### F-04.10 Rekonstruktion externer Ergebnisse

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.08, F-05.02
- Quelle: ARCH §13.2 (numerische und externe symbolische Ergebnisse)
- Bearbeiter: offen · Nachweise: offen

Ergebnisse aus SymPy, SMT oder Numerik werden erst nach Rekonstruktion in Lean oder nach Zertifikatsprüfung als formal gültig übernommen.

- [ ] Eine SymPy-Identität wird als Lean-Ziel rekonstruiert und geprüft.
- [ ] Ohne Rekonstruktion bleibt die Erkenntnisstufe `SYMBOLICALLY_DERIVED`.
