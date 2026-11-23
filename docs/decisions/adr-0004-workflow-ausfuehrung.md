# ADR-0004 Workflow- und Task-Ausführung

- Status: `accepted`
- Datum: 2026-11-23
- Löst: OD-04
- Betroffene Features: F-07.03, F-08.05

## Kontext

ARCH §17.1 empfiehlt eine eigene typisierte Python-Engine und später eine Task Queue. ARCH §17.2 rät, das System zu Beginn nicht als verteilten Cluster zu betreiben. UI §20 (Stufe 1) verlangt Pause, Resume und Stop über bestätigte Backendkommandos. Der Live-Stream läuft über FastAPI mit SSE oder WebSocket (UI §19). Es gelten die Invarianten Append-only Events und Keine Historienmutation.

## Optionen

| Option | Vorteile | Nachteile |
| --- | --- | --- |
| A: Synchron im Prozess | Am einfachsten | Ein Stream und Steuerbefehle sind nicht möglich, solange ein Run läuft. Das widerspricht UI §20. |
| B: `asyncio` im API-Prozess, Lean, Solver und Modelle als Subprozesse oder in Thread-Pools | Live-Events, Pause, Resume und Stop sind im selben Prozess einfach umzusetzen. Es gibt keine zusätzliche Infrastruktur. | Es skaliert auf einen Rechner. Stürzt der Prozess ab, endet der Run und muss aus einem Checkpoint fortgesetzt werden. |
| C: Externe Task Queue (z. B. Celery, Arq oder Dramatiq) | Robust und verteilbar | Zusätzliche Infrastruktur und Komplexität, die M1 nicht braucht |

## Empfehlung

Option B. Pause und Resume werden kooperativ umgesetzt: Die Engine prüft zwischen zwei Suchschritten den Steuerzustand. Ein Checkpoint ist ein Snapshot des Suchzustands und wird als Ereignis an den Eventstrom angehängt. Resume rekonstruiert den Zustand aus dem letzten Snapshot und den folgenden Events. Stop beendet laufende Subprozesse mit einem Timeout. Die Engine-Schnittstelle wird so geschnitten, dass sich eine Queue (Option C) später dahinter einsetzen lässt.

## Entscheidung

Angenommen am 2026-11-23: Option B wie empfohlen.

## Folgen

F-07.03 und F-08.05 werden `ready`, sobald ihre übrigen Abhängigkeiten `done` sind. CPU-lastige Arbeit wie Lean oder SymPy darf die Event-Loop nicht blockieren und läuft deshalb in Subprozessen. Es bleibt das Risiko, dass ein Prozessabsturz den laufenden Schritt verliert. Checkpoints in Schrittgranularität begrenzen diesen Verlust.
