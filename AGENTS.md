# Regeln für Agenten

Diese Datei gilt für jeden Agenten, der in diesem Repository arbeitet. Die vollständigen Regeln stehen in [docs/backlog/WORKFLOW.md](docs/backlog/WORKFLOW.md). Bei einem Widerspruch zwischen beiden Dateien gilt WORKFLOW.md, und der Widerspruch wird gemeldet.

## Projekt

MathLab ist ein agentisches System für mathematische Forschung und Beweisführung. Sprachmodelle schlagen vor, der formale Prüfer entscheidet. Das Repository enthält bisher nur Dokumentation. Den Einstieg beschreibt [docs/README.md](docs/README.md).

## Einstieg

1. [docs/backlog/BACKLOG.md](docs/backlog/BACKLOG.md) öffnen und den Abschnitt „Now“ lesen.
2. Ein Feature mit Status `ready` wählen. P0 geht vor P1, der laufende Meilenstein vor späteren.
3. In der Epic-Datei Status `in-progress` und Bearbeiter setzen. Diese Änderung wird vor der Umsetzung oder im selben Commit festgehalten.
4. Die im Feature genannten Quellabschnitte in [docs/research/](docs/research/) lesen.
5. Umsetzen, testen und die Nachweise im Feld „Nachweise“ eintragen.
6. Status auf `review` oder `done` setzen, Übersichtstabelle der Epic-Datei, [BACKLOG.md](docs/backlog/BACKLOG.md) und [ROADMAP.md](docs/backlog/ROADMAP.md) nachziehen.
7. Abhängige Features prüfen und auf `ready` setzen, wenn ihre Abhängigkeiten `done` und ihre offenen Entscheidungen entschieden sind.

## Definition of Ready

Alle Abhängigkeiten sind `done`. Keine verknüpfte offene Entscheidung aus [OPEN_DECISIONS.md](docs/decisions/OPEN_DECISIONS.md) ist offen. Jedes Akzeptanzkriterium lässt sich durch einen Test oder eine Prüfung belegen.

## Definition of Done

Jedes Akzeptanzkriterium ist abgehakt und durch einen ausgeführten Nachweis belegt. Formatter, Linter und Tests sind gelaufen, das Ergebnis steht unter „Nachweise“. Betroffene Dokumentation ist aktualisiert. Die Änderung ist als Conventional Commit auf `develop` festgehalten.

## Grenzen

Ein Agent bearbeitet genau ein Feature. Pro Feature arbeitet höchstens ein Agent. Es werden keine weiteren Agenten pro Datei, Prüfdimension oder Befund gestartet.

Was beim Arbeiten zusätzlich auffällt, wird als neues Feature mit Status `todo` angelegt und nicht nebenbei umgesetzt. Eine fachliche Frage, die sich aus Code und Quelle nicht beantworten lässt, wird als OD-Eintrag erfasst, und das Feature erhält den Status `blocked`.

Gearbeitet wird auf `develop`. Auf `main` wird nicht direkt gearbeitet. Jeder Push braucht eine neue ausdrückliche Freigabe des Benutzers. Hooks und Signaturen werden nicht umgangen.

Die Dateien unter [docs/research/](docs/research/) bleiben unverändert. Secrets und personenbezogene Daten gehören nicht in Code, Events, Prompts, Logs, Tests oder Commits.

## Fachliche Invarianten

| Invariante | Bedeutung |
| --- | --- |
| Kein `VERIFIED` ohne Prüfnachweis | Nur das Verifikations-Backend setzt `VERIFIED` bzw. `FORMALLY_VERIFIED`. Agentenaussagen und UI-Aktionen können es nicht. |
| Unveränderliche Zielaussage | Der Hash der formalen Zielaussage ändert sich nach Bestätigung nicht. |
| Append-only Events | Ereignisse werden nie geändert oder gelöscht. Korrekturen sind neue Ereignisse. |
| Evidenz ist kein Beweis | Numerische und symbolische Ergebnisse behalten ihre Erkenntnisstufe, bis sie formal geprüft sind. |
| Blind Rediscovery | Im Modus `BLIND_REDISCOVERY` hat kein Agent Zugriff auf Referenzlösungen. |
| Keine Historienmutation | Eingriffe erzeugen neue Versuche, Branches oder Runs. |
| Getrennte Statusräume | Agentenstatus, Erkenntnisstufe und Verifikationsstatus sind getrennte Typen, siehe [glossary.md](docs/glossary.md). |

## Sprache

Prosa in Dokumentation und Features ist Deutsch. Codebezeichner, Dateinamen, Eventnamen, Schemas, Logs und Testnamen sind Englisch.
