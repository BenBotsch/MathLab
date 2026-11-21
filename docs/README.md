# Dokumentation

MathLab ist ein agentisches System für mathematische Forschung und Beweisführung. Sprachmodelle schlagen Beweisschritte, Strategien und Vermutungen vor. Über ihre Gültigkeit entscheidet ein formaler Prüfer wie Lean 4. Das Projekt steht vor der Implementierung. Dieses Verzeichnis enthält die Konzepte, das Backlog und die Entscheidungen.

## Inhalt

| Pfad | Inhalt |
| --- | --- |
| [research/](research/) | Unveränderte Konzeptdokumente. ARCH ist das [Forschungs- und Architekturkonzept](research/Mathematisches_Beweissystem_Forschungs_und_Architekturkonzept.md), UI das [Konzept für das Research Control Center](research/Mathematisches_Beweissystem_UI_Research_Control_Center.md). |
| [glossary.md](glossary.md) | Begriffe und die getrennten Statusräume für Erkenntnisstufe, Verifikation, Agenten und Beweisknoten |
| [backlog/BACKLOG.md](backlog/BACKLOG.md) | Statusübersicht aller Epics und Features mit den Abschnitten Now, Next und Later |
| [backlog/ROADMAP.md](backlog/ROADMAP.md) | Meilensteine M1 bis M6 mit Exit-Kriterien und der Reihenfolge in M1 |
| [backlog/WORKFLOW.md](backlog/WORKFLOW.md) | Status, Definition of Ready und Done, Ablauf für Agenten und fachliche Invarianten |
| [backlog/TRACEABILITY.md](backlog/TRACEABILITY.md) | Zuordnung jedes Quellabschnitts zu Features |
| [backlog/epics/](backlog/epics/) | Ein Dokument pro Epic, die Features stehen als Abschnitte darin |
| [backlog/templates/](backlog/templates/) | Vorlage für neue Epics |
| [decisions/](decisions/) | ADR-Verfahren, ADR-Vorlage und [offene Entscheidungen](decisions/OPEN_DECISIONS.md) |

## Leseweg

Für einen Überblick genügen die Abschnitte 1, 4 und 19 von ARCH und die Abschnitte 1 und 20 von UI. Danach zeigen [ROADMAP.md](backlog/ROADMAP.md) und [BACKLOG.md](backlog/BACKLOG.md), was in welcher Reihenfolge entsteht.

Wer ein Feature umsetzt, liest zuerst [AGENTS.md](../AGENTS.md) und [WORKFLOW.md](backlog/WORKFLOW.md), dann die Epic-Datei und zuletzt die im Feature genannten Quellabschnitte. Das Feature ist die Arbeitsanweisung. Die Quelle liefert den fachlichen Hintergrund.

## Quellverweise

Features verweisen mit `ARCH §x.y` und `UI §x.y` auf die Abschnitte der beiden Konzeptdokumente. Die Dateien unter [research/](research/) werden nicht bearbeitet. Ergänzungen und Abweichungen stehen in Features, ADRs oder offenen Entscheidungen.
