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
| F-04.03 | Isolierte Beweisprüfung | `done` | P0 | M1 |
| F-04.04 | Zielabgleich | `done` | P0 | M1 |
| F-04.05 | Axiomreport und `sorry`-Prüfung | `done` | P0 | M1 |
| F-04.06 | Unabhängige Nachprüfung | `done` | P1 | M1 |
| F-04.07 | Archiv der Verifikationsartefakte | `done` | P0 | M1 |
| F-04.08 | Prüfung einzelner Beweispflichten | `done` | P0 | M1 |
| F-04.09 | Verifikations-Cache und Revalidierung | `done` | P1 | M2 |
| F-04.10 | Rekonstruktion externer Ergebnisse | `ready` | P1 | M2 |
| F-04.11 | Spike Lean-Interaktionsschicht | `done` | P0 | M1 |
| F-04.12 | Kontrolliert äquivalente Zielform | `todo` | P1 | M2 |
| F-04.13 | Von Lean unabhängiger Kernel-Checker | `todo` | P1 | M2 |
| F-04.14 | Reproduktion mit Nachprüfung | `todo` | P1 | M2 |

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

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.02, F-24.01
- Quelle: ARCH §7.3 (Schritt 1), §21 (gefährlicher generierter Code)
- Bearbeiter: Claude (Agent) · Nachweise: `src/mathlab/engines/lean_check.py` (`LeanChecker` als `VerificationEngine`, ein `lean`-Lauf pro Beweis in `run_sandboxed`), `docker/lean.Dockerfile` (Skript `/home/lean/bin/lean-check` mit festem `LEAN_PATH`, weil `lake env` git aufruft), `SandboxLimits.user` in `src/mathlab/sandbox.py` (numerisch, nie root; der Prüfer läuft als Image-Benutzer `lean`, UID 1000, weil der Mathlib-Cache nur für ihn lesbar ist). Tests in `tests/test_lean_check.py` (8, davon 4 gegen den Container) und `tests/test_sandbox.py` (6 neue). Am 2026-11-25: `ruff format --check` und `ruff check` ohne Befund, `mypy` (strict, 78 Dateien) ohne Befund, `pytest` 691 bestanden und 39 übersprungen ohne Testumgebung, 730 bestanden mit Datenbank und allen Images. Dabei gefunden und abgedeckt: Lean v4.36 schreibt ``declaration uses `sorry` `` mit Backticks und Meldungen teils als `error(code):`. Axiomreport und Zielabgleich folgen in F-04.05 und F-04.04.

Vollständige Lean-Quelle aus Zielaussage und Beweis wird in einer Sandbox ohne Netz und mit Ressourcenlimits geprüft.

- [x] Ein Beweis mit Endlosschleife wird nach Zeitlimit mit `RESOURCE_EXHAUSTION` beendet. Geprüft mit `#eval` einer `partial def`-Endlosschleife und 30 s Zeitlimit: `EngineTimeoutError` mit `RESOURCE_EXHAUSTION`.
- [x] Die Prüfung hat keinen Netzzugriff. Der Container läuft mit `--network none`. Eine Probe im Prüfcontainer sieht nur die Schnittstelle `lo`.

### F-04.04 Zielabgleich

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.03, F-01.03
- Quelle: ARCH §7.3 (Schritt 5), §13.1, §13.2, §18.4
- Bearbeiter: Claude (Agent) · Nachweise: `goal_mismatches` und `LeanChecker(targets=...)` in `src/mathlab/engines/lean_check.py`. Vor jedem Lean-Lauf holt der Prüfer über `targets` das `ConfirmedStatement` zur `statement_id`. Abgelehnt mit `EngineFailureError` und `SEMANTIC_MISMATCH` wird, wenn kein bestätigtes Ziel existiert oder `statement_id`, `statement_hash`, der Hash des angefragten `lean_code` unter Importen und Toolchain des Ziels oder die Toolchain des Prüfers (`TOOLCHAIN`, `leanprover/lean4:v4.36.0`) abweicht. Dann startet kein Container. Kompiliert wird danach die bestätigte Aussage mit ihren Importen, nie die Kopie aus der Anfrage. Ohne `targets` lehnt der Prüfer jede Anfrage ab. Tests in `tests/test_lean_check.py` (6 neue, davon 2 gegen den Container). Am 2026-11-26: `ruff format --check` und `ruff check` ohne Befund, `mypy` (strict, 78 Dateien) ohne Befund, `pytest` mit Lean-Image 714 bestanden und 30 übersprungen (ohne Datenbank und SymPy-Image). Kontrolliert äquivalente Formen mit eigenem Nachweis sind nicht umgesetzt und als F-04.12 erfasst.

Das bewiesene Theorem muss exakt der Zielaussage mit dem bestätigten Hash entsprechen oder einer kontrolliert äquivalenten Form mit eigenem Nachweis.

- [x] Ein Beweis eines abgeschwächten Ziels wird abgelehnt. Im Container: `n + 0 = n \/ True` mit `Or.inr trivial` kompiliert als eigenes Ziel, gegen das bestätigte Ziel `n + 0 = n` folgt `SEMANTIC_MISMATCH`.
- [x] Ein Beweis mit veränderter Zielaussage wird abgelehnt, auch wenn er kompiliert. Jede Abweichung im normalisierten `lean_code`, in Hash oder Toolchain führt ohne Lean-Lauf zu `SEMANTIC_MISMATCH`. Eine Anfrage, die nur durch Normalisierung abweicht, wird gegen die bestätigte Aussage geprüft.

### F-04.05 Axiomreport und `sorry`-Prüfung

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.03
- Quelle: ARCH §7.3 (Schritt 2), §13.2, §21
- Bearbeiter: Claude (Agent) · Nachweise: `src/mathlab/engines/lean_check.py` (`AxiomPolicy`, `AxiomReport`, `parse_axiom_report`, `LeanChecker.check` liefert Antwort und Report; `verify` lehnt jedes nicht erlaubte oder fehlende Axiom ab) und [docs/reference/lean-axioms.md](../../reference/lean-axioms.md). Der Prüfer hängt `#print axioms _root_.<name>` hinter einer zufälligen Markierung an; gewertet wird nur die Ausgabe nach der letzten Markierung, damit ein Beweis keinen Report fälschen und kein `namespace` den Namen umlenken kann. Tests in `tests/test_lean_check.py` (16, davon 7 gegen den Container). Am 2026-11-25: `ruff format --check` und `ruff check` ohne Befund, `mypy` (strict, 78 Dateien) ohne Befund, `pytest` 696 bestanden und 42 übersprungen ohne Testumgebung, 738 bestanden mit Datenbank und allen Images. `native_decide` erscheint unter Lean v4.36 als Hilfsaxiom `<name>._native.native_decide.ax_…` und wird als zusätzliches Vertrauen abgelehnt.

Für jeden geprüften Beweis entsteht ein Report der verwendeten Axiome. `sorry`, `sorryAx`, benutzerdefinierte Axiome und andere unzulässige Vertrauenskonstrukte führen zur Ablehnung. Mechanismen mit zusätzlichen Vertrauensannahmen werden im Report ausgewiesen (ARCH §13.2).

- [x] Ein Beweis mit `sorry` wird abgelehnt. Im Container: `by sorry` liefert `sorryAx` im Report und keinen gültigen Schritt.
- [x] Ein Beweis mit eigenem `axiom` wird abgelehnt. Im Container: `axiom bad : False` erscheint unter `custom`, die Antwort hat keinen gültigen Schritt. `native_decide` wird als zusätzliches Vertrauen abgelehnt.
- [x] Die erlaubten Standardaxiome sind konfiguriert und dokumentiert: `STANDARD_AXIOMS` (`propext`, `Classical.choice`, `Quot.sound`) als Voreinstellung von `AxiomPolicy`, beschrieben in `docs/reference/lean-axioms.md`.

### F-04.06 Unabhängige Nachprüfung

- Status: `done` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-04.05
- Quelle: ARCH §7.3 (Schritt 4), §13.2; Lean-Dokumentation „Validating a Lean Proof“
- Bearbeiter: Claude · Nachweise: Werkzeug ist `leanchecker`, der in Lean v4.36.0 enthaltene Nachfolger von `lean4checker`. `docker/lean.Dockerfile` erhält `/home/lean/bin/lean-recheck`. `LeanChecker` prüft jeden sonst vollständigen Beweis in einer zweiten, frischen Sandbox nach (`run_recheck`, `with_recheck`, Option `fresh_recheck` für `--fresh`). Ein Fehlschlag lehnt den Beweis ab. Der `RecheckReport` steht in `CheckOutcome`, in den Meldungen des `VerificationResult` und als Artefakt `recheck` im Manifest (F-04.07). `tests/test_lean_recheck.py` mit 9 Tests, davon 2 Containertests. Ein Beweis von `False` über `debug.skipKernelTC` besteht die erste Prüfung (Exit 0, keine Axiome) und wird erst durch die Nachprüfung abgelehnt. `--fresh` mit Mathlib dauerte im Versuch über sechs Minuten und ist deshalb nicht Standard. Beschrieben in `docs/reference/lean-axioms.md`. `ruff format`, `ruff check`, `mypy` ohne Befund. `pytest` mit `MATHLAB_TEST_LEAN_IMAGE=mathlab-lean:latest`: 737 passed, 30 skipped (Datenbank-, Sandbox- und SymPy-Image fehlen).

Verifizierte Beweise werden zusätzlich mit `lean4checker --fresh` oder dem jeweils dokumentierten Mechanismus erneut geprüft. Bei hohem Schutzbedarf ist ein unabhängiger Checker vorgesehen. Die Werkzeugwahl erfolgt gemäß der aktuellen Lean-Dokumentation.

- [x] Die Nachprüfung läuft für jeden als `VERIFIED` markierten Beweis und ist im Artefakt vermerkt.

### F-04.07 Archiv der Verifikationsartefakte

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.05, F-02.07
- Quelle: ARCH §7.3 (Schritt 6)
- Bearbeiter: Claude (Agent) · Nachweise: `src/mathlab/engines/verification_archive.py` (`archive_check`, `load_manifest`, `reproduce`, `VerificationManifest`), `LeanChecker.check_outcome` und `CheckOutcome` in `src/mathlab/engines/lean_check.py`, neues Feld `VerificationResult.archive_artifact` (Schema `schemas/core/VerificationResult.schema.json` neu erzeugt). Pro Prüfung entstehen vier content-addressed Artefakte (ADR-0006): kompilierte Lean-Quelle, Log mit Exitcode, stdout und stderr, Axiomreport und ein Manifest. Das Manifest nennt die bestätigte Zielaussage mit Hash, Toolchain, Prüferversion, Image, optional die Docker-Image-ID, Sandbox-Limits, Axiompolitik, Marker und den Environment-Fingerprint. `proof_artifact` zeigt auf die Quelle, `archive_artifact` auf das Manifest. Tests in `tests/test_verification_archive.py` (7, davon 1 gegen den Container). Am 2026-11-26: `ruff format --check` und `ruff check` ohne Befund, `mypy` (strict, 80 Dateien) ohne Befund, `pytest` mit Lean-Image 721 bestanden und 30 übersprungen (ohne Datenbank, Sandbox- und SymPy-Image). Annahme: Image-ID und Environment-Fingerprint liefert der Aufrufer (`docker_image_id`, `collect_environment`), weil der Prüfer keinen Repository-Kontext hat. Die Verknüpfung über Events folgt mit dem Verification Agent (F-07.09).

Beweisquelle, Axiomreport, Log und Fingerprints werden als Artefakte gespeichert und mit dem `VerificationResult` verknüpft.

- [x] Jedes `VerificationResult` verweist auf vollständige Artefakte. `archive_check` erzeugt das Ergebnis nur zusammen mit dem Archiv. `load_manifest` prüft, dass alle genannten Artefakte existieren und zu ihrem Hash passen, und weist ein fremdes oder verändertes Archiv ab.
- [x] Aus den Artefakten lässt sich die Prüfung reproduzieren. `reproduce` kompiliert die archivierte Quelle mit den protokollierten Einstellungen neu. Im Container ergibt der Beweis von `n + 0 = n` erneut einen gültigen Schritt mit denselben Axiomen.

### F-04.08 Prüfung einzelner Beweispflichten

- Status: `done` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-04.04
- Quelle: ARCH §3.1 (Verifikation einzelner Lemmata), §7.2 (Schritt 6); UI §20 (Kriterium 2)
- Bearbeiter: Claude · Nachweise: `src/mathlab/engines/obligations.py` mit `check_obligation`. Die Ereignisse `proof.step.verified` und `lemma.verified` erhalten das Feld `artifact` (Manifest aus F-04.07). Ein abgelehntes Lemma nutzt `proof.step.rejected` mit der Lemma-ID als `step_id`, weil der Katalog kein `lemma.rejected` kennt. `tests/test_obligations.py` mit 7 Tests, davon ein Containertest: Lemma `VERIFIED`, Hauptziel mit `sorry` `REJECTED`, Übergang des Hauptziels nach `FORMALLY_VERIFIED` scheitert. `ruff format`, `ruff check`, `mypy` ohne Befund. `pytest` mit `MATHLAB_TEST_LEAN_IMAGE=mathlab-lean:latest`: 728 passed, 30 skipped (Datenbank-, Sandbox- und SymPy-Image fehlen).

Teilziele und Lemmata werden unabhängig vom Gesamterfolg geprüft. Ergebnis ist ein Ereignis `proof.step.verified`, `lemma.verified` oder `proof.step.rejected`.

- [x] Ein verifiziertes Teilziel erzeugt das Ereignis mit Verweis auf das Artefakt.
- [x] Ein Lemma kann `VERIFIED` sein, während das Hauptziel offen bleibt.

### F-04.09 Verifikations-Cache und Revalidierung

- Status: `done` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.07
- Quelle: ARCH §18.4
- Bearbeiter: Claude · Nachweise: `src/mathlab/engines/verification_cache.py` mit `VerificationCache`, `CachedChecker`, `cache_key` und `dependencies_from_manifest`. Der Schlüssel umfasst Zielhash, Beweis, Toolchain, alle Paketrevisionen aus `lean/lake-manifest.json`, Checker-Version, Axiompolitik und Recheck-Modus. Ein Treffer liefert das archivierte `VerificationResult` und wird gegen das Archiv geprüft. `mark_revalidation` markiert Einträge mit abweichenden Abhängigkeiten, `revalidation_due` listet sie, und markierte Einträge werden nicht ausgeliefert. `tests/test_verification_cache.py` mit 11 Tests, davon ein Containertest (zweite identische Prüfung ohne Lean-Lauf). `ruff format`, `ruff check`, `mypy` ohne Befund. `pytest` mit `MATHLAB_TEST_LEAN_IMAGE=mathlab-lean:latest`: 748 passed, 30 skipped (Datenbank-, Sandbox- und SymPy-Image fehlen).

Cache über den Hash von Aussage, Beweis, Toolchain und Abhängigkeiten. Wechselt die Mathlib-Version, werden abhängige Zertifikate erneut geprüft.

- [x] Identische Prüfanfragen werden aus dem Cache beantwortet.
- [x] Nach einem Versionswechsel sind betroffene Ergebnisse als „zu revalidieren“ markiert.

### F-04.10 Rekonstruktion externer Ergebnisse

- Status: `ready` · Priorität: P1 · Meilenstein: M2
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

### F-04.12 Kontrolliert äquivalente Zielform

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.04
- Quelle: ARCH §13.2 (kontrolliert äquivalente Form)
- Bearbeiter: offen · Nachweise: offen

Der Zielabgleich (F-04.04) akzeptiert bisher nur die exakt bestätigte Aussage. Eine abweichende Form gilt nur, wenn ein eigener, formal geprüfter Äquivalenznachweis zur bestätigten Aussage vorliegt und archiviert ist.

- [ ] Ein Beweis einer äquivalenten Form mit geprüftem Äquivalenzbeweis wird akzeptiert und verweist auf diesen Nachweis.
- [ ] Ohne Äquivalenzbeweis oder mit nur einseitiger Implikation wird die Form abgelehnt.

### F-04.13 Von Lean unabhängiger Kernel-Checker

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.06
- Quelle: ARCH §7.3 (Schritt 4), §13.2; Lean-Dokumentation „Validating a Lean Proof“
- Bearbeiter: offen · Nachweise: offen

Bei hohem Schutzbedarf wird ein verifizierter Beweis zusätzlich von einem Kernel geprüft, der nicht aus dem Lean-Code stammt, etwa `nanoda` oder `lean4lean`. Die Werkzeugwahl folgt der aktuellen Lean-Dokumentation und wird als ADR festgehalten. F-04.06 nutzt bisher nur `leanchecker` aus der Lean-Toolchain.

- [ ] Ein Beweis mit Schutzbedarf „hoch“ wird zusätzlich vom unabhängigen Checker geprüft, das Ergebnis steht im Archiv.
- [ ] Lehnt der unabhängige Checker ab, ist der Beweis nicht `VERIFIED`.

### F-04.14 Reproduktion mit Nachprüfung

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-04.06, F-04.07
- Quelle: ARCH §7.3 (Schritte 4 und 6)
- Bearbeiter: offen · Nachweise: offen

`reproduce` (F-04.07) wiederholt bisher nur die erste Lean-Prüfung. Die Reproduktion führt künftig auch die archivierte Nachprüfung mit demselben Modus (`fresh` oder nicht) erneut aus und vergleicht beide Ergebnisse.

- [ ] Die Reproduktion eines archivierten Beweises meldet das Ergebnis der erneuten Nachprüfung.
- [ ] Ein abweichendes Nachprüfergebnis ist im Rückgabewert erkennbar.
