# ADR-0001 Client-Plattform der Oberfläche

- Status: `accepted`
- Datum: 2026-11-23
- Löst: OD-01
- Betroffene Features: F-15.01 und alle UI-Epics E15 bis E22

## Kontext

Die beiden Konzeptdokumente widersprechen sich.

- ARCH §17.1 empfiehlt Flutter als Windows/Linux-Desktop-Client und React nur optional für ein Forschungsdashboard.
- UI §19 nennt „UI: React + TypeScript“ mit React Flow, Cytoscape.js, Plotly, KaTeX/MathJax und Monaco. Für die Desktop-Verteilung nennt es „React in Desktop-Wrapper oder Flutter-Shell“. UI §19.1 empfiehlt zuerst ein lokales React-/TypeScript-Frontend über FastAPI. Flutter soll höchstens später als äußere Shell mit eingebetteten Webflächen dienen. Eine Neuimplementierung der Graphfunktionen in Flutter lohnt sich nur, wenn der Vorteil die Kosten rechtfertigt.

Das UI-Konzept ist das spezifischere Dokument. Die Kernansichten in M1 sind Proof Search Graph, Inspector, Timeline und Agentenliste (UI §20, Stufe 1). Sie stützen sich auf Graph-, Formel- und Editorbibliotheken, die es im Web-Ökosystem gibt.

## Optionen

| Option | Vorteile | Nachteile |
| --- | --- | --- |
| A: React + TypeScript im Browser, lokales FastAPI-Backend | Alle Bibliotheken aus UI §19 lassen sich direkt nutzen. Es gibt keinen Paketierungsaufwand, und die Iteration ist am schnellsten. | Es entsteht kein eigenständiges Desktop-Programm. Der Start läuft über Backend und Browser. |
| B: Wie A, zusätzlich ein Desktop-Wrapper (Tauri oder Electron) | Gleicher Code wie A und ein echtes Fenster unter Windows und Linux | Zusätzlicher Build- und Signierungsaufwand, der in M1 keinen fachlichen Nutzen bringt |
| C: Flutter-Desktop mit eingebetteten Web-Views für die Graphen | Schließt an bestehende Flutter-Projekte an (UI §19.1). | Zwei UI-Technologien und eine Brücke für den Zustand zwischen Dart und JS. Die Graphansichten brauchen trotzdem React. Die Web-View-Unterstützung unter Linux-Desktop ist weniger ausgereift. |

## Empfehlung

Option A für M1. Die Architektur hält Option B offen: Das Frontend spricht nur über die versionierte API (F-14.01) mit dem Backend, und ein Wrapper lässt sich später ohne Umbau ergänzen. Option C wird nicht weiterverfolgt, solange kein konkreter Grund aus bestehenden Flutter-Projekten vorliegt.

Ob Code aus Flutter-Projekten übernommen werden soll, muss der Benutzer entscheiden.

## Entscheidung

Angenommen am 2026-11-23: Option A, React und TypeScript im Browser gegen ein lokales FastAPI-Backend. Bestehende Flutter-Projekte spielen keine Rolle. Ein Desktop-Wrapper (Option B) bleibt als spätere Erweiterung möglich.

## Folgen

Bei Option A wird F-15.01 `ready`, sobald F-00.02 `done` ist. OD-05 muss dann die Frontend-Paketverwaltung festlegen (Empfehlung: pnpm). Es bleibt das Risiko, dass später doch ein Desktop-Client gefordert wird. Option B begrenzt dieses Risiko.
