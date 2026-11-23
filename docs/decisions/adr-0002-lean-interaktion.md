# ADR-0002 Lean-Interaktionsschicht

- Status: `proposed`
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

Die Angaben zu Wartungsstand und Versionsunterstützung stammen aus meinem Kenntnisstand und sind nicht geprüft. Der Spike muss sie belegen.

## Empfehlung

Für M1 Option A als Interaktionsschicht hinter einem providerneutralen Adapter (F-01.04 Engine-Contracts). Option C ist die Rückfallebene. LeanDojo wird erst für den Wissensgraphen und die Datensatzextraktion (M3) erneut bewertet. Lean läuft im Linux-Container, Windows wird nur über Container oder WSL unterstützt.

Vor der Annahme soll ein Spike mit festen Kriterien laufen:

1. Lean und Mathlib in der gepinnten Version starten.
2. Ein Golden-Theorem aus F-11.01 laden und die Goals auslesen.
3. Taktiken ausführen, verzweigen und zu einem früheren Zustand zurückkehren.
4. Laufzeit und Speicherbedarf beim Start und pro Taktik messen.
5. Lizenz und letzte Releases festhalten.

## Entscheidung

Offen. Der Benutzer hat am 2026-11-23 festgelegt, dass zuerst der Spike F-04.11 läuft. Danach wird dieser ADR angenommen oder angepasst.

## Folgen

F-04.02 wird nach der Entscheidung `ready`. Die endgültige Verifikation bleibt ein separater `lake build`-Lauf. Ein Fehler in der Interaktionsschicht kann deshalb nie `VERIFIED` erzeugen. Es bleibt das Risiko, dass Lean-Versionssprünge die Anbindung brechen. Der Adapter und das Toolchain-Pinning begrenzen dieses Risiko.
