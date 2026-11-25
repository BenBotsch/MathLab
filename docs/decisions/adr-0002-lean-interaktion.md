# ADR-0002 Lean-Interaktionsschicht

- Status: `accepted`
- Datum: 2026-11-23
- Löst: OD-02
- Betroffene Features: F-04.02, mittelbar E04 und E08

## Kontext

ARCH §17.1 nennt „LeanDojo / Pantograph“ für den Zugang zu Werkzeugen, Proof States und Taktiken. ARCH §13.1 legt fest, dass Lean der Trusted Checker ist. Die Interaktionsschicht ist also nicht Teil des Trusted Core. Die abschließende Prüfung muss ein vollständiger Lean-Build der Beweisdatei übernehmen. Lean und Mathlib werden gepinnt (F-00.03). ARCH §17.3 sieht vor, Lean CPU-basiert zu betreiben, und F-00.04 sieht eine Container-Umgebung vor.

## Optionen

| Option | Vorteile | Nachteile |
| --- | --- | --- |
| A: Pantograph (mit Python-Anbindung PyPantograph) | Wurde gezielt als Maschine-zu-Maschine-Schnittstelle für Proof Search gebaut: Goals, Taktikausführung, Branching. Es läuft als eigenständiger Prozess gegen ein Lean-Projekt. | Kleinere Community. Die Kompatibilität mit der gepinnten Lean-Version muss geprüft werden. |
| B: LeanDojo | Bekannt aus der Forschung und bietet Tracing, Datenextraktion und Premise-Daten für Retrieval (E10). | Stärker auf Datensatzextraktion und Repository-Tracing ausgerichtet, und das Tracing ist aufwendig. Nach meinem Kenntnisstand läuft es nicht nativ unter Windows, sondern nur unter Linux, macOS oder WSL. |
| C: Lean REPL (leanprover-community/repl) mit eigenem dünnem Adapter | Minimal, wird von der Community gepflegt, JSON über stdin/stdout. | Branching und Proof-State-Verwaltung müssen selbst gebaut werden. |

Die Angaben zu Wartungsstand und Versionsunterstützung in der Tabelle stammen aus dem Kenntnisstand vor dem Spike. Die geprüften Angaben stehen im nächsten Abschnitt.

## Ergebnis des Spikes F-04.11 (2026-11-25)

Geprüft gegen Lean `v4.36.0` und Mathlib `v4.36.0` aus `mathlab-lean:latest`. Das Spike-Image steht in `docker/lean-spike.Dockerfile`, das Skript in `spikes/lean_interaction.py`.

| Werkzeug | Lizenz | Stand | Ergebnis mit v4.36.0 |
| --- | --- | --- | --- |
| Lean REPL | Apache-2.0 | Tag `v4.36.0` (1b9fdf8a), daneben `v4.37.0-rc1`. Letzter Push am 2026-11-19 | Baut und läuft |
| Pantograph | Apache-2.0 | Keine GitHub-Releases. Letzter Tag `v0.3.17` (Lean v4.31.0, 2026-08-14). Branch `dev` (6479c9bb, 2026-11-15) steht auf Lean v4.35.0 | Baut nicht |
| PyPantograph | Apache-2.0 | Release `v0.3.15` (2026-04-26), bindet Pantograph als Submodul ein. Letzter Push am 2026-10-30 | Nicht gebaut, weil Pantograph nicht baut |

Pantograph `dev` scheitert mit v4.36.0 an zwei Stellen. Zum einen fehlt in `Pantograph/Frontend/InfoTree.lean` der Match-Fall für das neue `Info.ofChoiceResolutionInfo`. Zum anderen gibt es `Lean.mkTheoremValEx` und `Lean.mkReducibilityHintsRegularEx` nicht mehr, die `Repl.lean` verwendet. Den ersten Fehler kann man lokal beheben, der zweite verlangt eine Portierung auf die geänderte Lean-API. Pantograph folgt Lean-Versionen erkennbar mit Verzögerung.

Mit der Lean REPL ist der Ablauf auf Golden-Aufgabe g09 demonstriert:

1. `import Mathlib` laden, dann die Aussage mit `sorry` öffnen. Die Antwort enthält Proof State 0 mit dem Goal.
2. `induction n with … | succ m ih => ?_` ausführen. Proof State 1 hat das Goal `case succ`.
3. `rw [Finset.sum_range_succ, mul_add, ih]` ergibt Proof State 2, `ring` danach Proof State 3 mit `Completed`.
4. Verzweigen ab Proof State 0. `norm_num` erzeugt einen neuen Zustand ohne Fortschritt, und `omega` scheitert mit einer Fehlermeldung, ohne einen Zustand zu erzeugen.
5. Rückkehr zu Proof State 1 und eine alternative Fortsetzung `(rw …; nlinarith)`, die ebenfalls `Completed` erreicht.

Alte Proof States bleiben gültig. Branching und Backtracking braucht deshalb keinen eigenen Mechanismus, sondern nur die Verwaltung der Zustandsnummern im Adapter.

| Messung (drei Läufe, Docker Desktop unter Windows) | Wert |
| --- | --- |
| Start bis geladenes `import Mathlib` | 32 bis 48 s |
| Aussage öffnen | etwa 0,12 s |
| Eine Taktik | 0,02 bis 0,15 s, `nlinarith` 0,9 s |
| Spitzenwert des Arbeitsspeichers (`/usr/bin/time -v`) | etwa 6,6 GiB |

Folgerungen für die Umsetzung:

- Der Import von Mathlib dominiert die Kosten. Ein REPL-Prozess wird deshalb pro Run oder Worker wiederverwendet und nicht pro Taktik gestartet. Die REPL kann Umgebungen zusätzlich mit `pickleTo` sichern, das ist noch nicht gemessen.
- Mit rund 6,6 GiB pro Prozess begrenzt der Arbeitsspeicher die Zahl paralleler Lean-Worker.
- Die REPL nimmt im Taktikmodus genau eine Taktik pro Befehl an. Folgen werden einzeln gesendet oder mit `(t1; t2)` gruppiert.
- `Completed` aus der REPL ist kein Prüfnachweis. `VERIFIED` setzt weiterhin nur der vollständige Lean-Build.

## Empfehlung

Nach dem Spike: Für M1 Option C, also die Lean REPL in der zur Toolchain passenden Version, hinter einem providerneutralen Adapter (F-01.04 Engine-Contracts). Pantograph unterstützt die gepinnte Lean-Version nicht. Es wird erneut bewertet, sobald ein Pantograph-Stand für die gepinnte Toolchain vorliegt, und kann dann hinter denselben Adapter treten. Vor dem Spike lautete die Empfehlung Option A mit C als Rückfallebene. LeanDojo wird erst für den Wissensgraphen und die Datensatzextraktion (M3) erneut bewertet. Lean läuft im Linux-Container, Windows wird nur über Container oder WSL unterstützt.

Der Spike lief mit diesen festen Kriterien:

1. Lean und Mathlib in der gepinnten Version starten.
2. Ein Golden-Theorem aus F-11.01 laden und die Goals auslesen.
3. Taktiken ausführen, verzweigen und zu einem früheren Zustand zurückkehren.
4. Laufzeit und Speicherbedarf beim Start und pro Taktik messen.
5. Lizenz und letzte Releases festhalten.

## Entscheidung

Angenommen am 2026-11-25 nach dem Spike F-04.11: Option C, die Lean REPL in der zur Toolchain passenden Version hinter einem providerneutralen Adapter. Pantograph wird neu bewertet, sobald es die gepinnte Toolchain unterstützt.

## Folgen

F-04.02 wird nach der Entscheidung `ready`. Die endgültige Verifikation bleibt ein separater `lake build`-Lauf. Ein Fehler in der Interaktionsschicht kann deshalb nie `VERIFIED` erzeugen. Es bleibt das Risiko, dass Lean-Versionssprünge die Anbindung brechen. Der Adapter und das Toolchain-Pinning begrenzen dieses Risiko.
