# E04 Formal Verification Engine

- Status: `in-progress` · Meilenstein: M1, Ausbau M2
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
| F-04.01 | Lean 4 und Mathlib einrichten | `done` | P0 | M1 |
| F-04.02 | Lean-Interaktionsadapter | `done` | P0 | M1 |
| F-04.03 | Isolierte Beweisprüfung | `ready` | P0 | M1 |
| F-04.04 | Zielabgleich | `todo` | P0 | M1 |
| F-04.05 | Axiomreport und `sorry`-Prüfung | `todo` | P0 | M1 |
| F-04.06 | Unabhängige Nachprüfung | `todo` | P1 | M1 |
| F-04.07 | Archiv der Verifikationsartefakte | `todo` | P0 | M1 |
| F-04.08 | Prüfung einzelner Beweispflichten | `todo` | P0 | M1 |
| F-04.09 | Verifikations-Cache und Revalidierung | `todo` | P1 | M2 |
| F-04.10 | Rekonstruktion externer Ergebnisse | `todo` | P1 | M2 |
| F-04.11 | Spike Lean-Interaktionsschicht | `done` | P0 | M1 |

## Features

### F-04.01 Lean 4 und Mathlib einrichten

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.03, F-00.04
- Quelle: ARCH §17.1, §22 (Schritt 1), §7.3 (Schritt 3)
- Bearbeiter: Claude (Agent) · Nachweise: Commit `feat: check the ARCH 15 odd sum example in the lean container` auf `develop`. Am 2026-11-24 gelaufen: `docker compose --profile engines build lean` (Lean v4.36.0, Mathlib `fc4f59e5`, Mathlib-Cache per `lake exe cache get`, `lake build` mit 6374 Jobs erfolgreich), `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy` (strict), `MATHLAB_TEST_LEAN_IMAGE=mathlab-lean:latest uv run pytest tests/test_lean_engine.py` (3 passed), `uv run pytest` mit PostgreSQL (625 passed, 2 übersprungen) und ohne (604 passed, 23 übersprungen). `lean/MathlabLean/OddSum.lean` beweist ARCH §15 wörtlich als `odd_sum` (Summe über `Icc 1 n` von `2k - 1` gleich `n^2`) und die 0-indizierte Form `odd_sum_range` per Induktion. Das Modul gehört zur Bibliothek und wird beim Image-Build geprüft. `#print axioms MathlabLean.odd_sum` im Container nennt nur `propext`, `Classical.choice` und `Quot.sound`, also kein `sorryAx`. Der Test liest `lean --version` aus dem Container in `collect_environment` ein: Lean- und Mathlib-Version stehen im Environment und verändern den Fingerprint. Annahme: Die Container-Tests laufen nur mit `MATHLAB_TEST_LEAN_IMAGE`, weil das Image mehrere GB groß ist und in CI nicht gebaut wird.

Lean-Projekt mit gepinnter Toolchain und Mathlib-Version, vorkompiliertem Cache und einem Beispielbeweis.

- [x] Der Beispielbeweis aus ARCH §15 (Summe ungerader Zahlen) kompiliert im Container.
- [x] Lean- und Mathlib-Version erscheinen im Environment-Fingerprint.

### F-04.02 Lean-Interaktionsadapter

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.01, F-01.04, F-04.11, F-00.01 (OD-02)
- Quelle: ARCH §17.1 (LeanDojo, Pantograph); LeanDojo in ARCH §2.1
- Bearbeiter: Claude (Agent) · Nachweise: `src/mathlab/engines/lean_repl.py` (`LeanReplEngine` mit `start`, `open_goal`, `apply_tactic`, `verify`; REPL im Image `mathlab-lean` per `docker/lean.Dockerfile`, Tag v4.36.0) und `tests/test_lean_repl.py` (12 Tests, davon 2 gegen den Container mit g09). Am 2026-11-25: `ruff format --check` und `ruff check` ohne Befund, `mypy` (strict, 76 Dateien) ohne Befund, `pytest` 681 bestanden und 35 übersprungen ohne Testumgebung, 716 bestanden mit Datenbank und allen Images. `verify` meldet nur, was die REPL sieht, und ist nicht die vertrauenswürdige Endprüfung. `VERIFIED` setzt erst F-04.03.

Python-Adapter, der Proof States liest, Taktiken ausführt und Fehler strukturiert zurückgibt. Implementiert den `VerificationEngine`-Contract und die für die Suche nötigen Zustandsoperationen.

- [x] Ein Ziel kann geöffnet, eine Taktik angewendet und der neue Proof State gelesen werden. Geprüft am Container mit g09, einschließlich Verzweigung von einem älteren Proof State.
- [x] Lean-Fehler werden auf den Fehlerkatalog (F-09.03) abgebildet. Eine gescheiterte Taktik liefert ein `TacticResult` mit `FailureClass`, eine nicht elaborierbare Aussage einen `EngineFailureError` mit `FailureCode`.
- [x] Timeouts und Abbruch funktionieren. Beide beenden den REPL-Container, danach meldet die Engine `EngineUnavailableError`.

### F-04.03 Isolierte Beweisprüfung

- Status: `ready` · Priorität: P0 · Meilenstein: M1
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

### F-04.11 Spike Lean-Interaktionsschicht

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.03, F-11.01
- Quelle: ARCH §13.1, §17.1; ADR-0002
- Bearbeiter: Claude (Agent) · Nachweise: `docker/lean-spike.Dockerfile` baut die Lean REPL am Tag `v4.36.0` gegen `mathlab-lean:latest`. `spikes/lean_interaction.py` demonstriert auf g09 Laden, Goals, Taktiken, Verzweigung ab Proof State 0 und Rückkehr zu Proof State 1, beide Pfade erreichen `Completed`. Gemessen über drei Läufe: Start mit `import Mathlib` 32 bis 48 s, Taktik 0,02 bis 0,9 s, Spitzenwert etwa 6,6 GiB. Pantograph `dev` (6479c9bb, Lean v4.35.0) baut mit v4.36.0 nicht: Es fehlt der Match-Fall `Info.ofChoiceResolutionInfo`, und `Lean.mkTheoremValEx` sowie `Lean.mkReducibilityHintsRegularEx` gibt es nicht mehr. PyPantograph wurde deshalb nicht gebaut. Lizenzen (alle Apache-2.0), Stände und Messungen stehen in ADR-0002, dessen Empfehlung jetzt Option C lautet. `ruff format`, `ruff check` und `mypy` (strict, jetzt auch über `spikes/`) ohne Befund; `pytest` mit Test-DB und allen Images 693 bestanden, ohne 660 bestanden, 33 übersprungen. ADR-0002 am 2026-11-25 vom Benutzer mit Option C angenommen.

Ein zeitlich begrenzter Spike prüft Pantograph (PyPantograph) und als Rückfall die Lean REPL gegen die gepinnte Lean- und Mathlib-Version. Das Ergebnis entscheidet OD-02.

- [x] Beide Werkzeuge starten mit der gepinnten Version im Linux-Container. Geprüft: Die Lean REPL startet, Pantograph baut mit v4.36.0 nicht (siehe Nachweise). Der Benutzer hat dieses Ergebnis mit ADR-0002 angenommen.
- [x] Ein Golden-Theorem aus F-11.01 wird geladen, die Goals werden ausgelesen.
- [x] Taktikausführung, Verzweigung und Rückkehr zu einem früheren Zustand sind demonstriert.
- [x] Startzeit, Zeit pro Taktik und Speicherbedarf sind gemessen.
- [ ] Lizenz und letzte Releases sind festgehalten. ADR-0002 ist mit dem Ergebnis aktualisiert und dem Benutzer vorgelegt.
