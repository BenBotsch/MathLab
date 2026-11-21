# Arbeitsablauf für Backlog und Agenten

Dieses Dokument legt fest, wie Epics und Features angelegt, gezogen, bearbeitet und abgeschlossen werden. Es gilt für Menschen und Agenten gleichermaßen. Die Kurzfassung für Agenten steht in [AGENTS.md](../../AGENTS.md).

## Aufbau

Jedes Epic ist eine Datei unter [epics/](epics/). Ein Epic beschreibt ein zusammenhängendes Ziel mit Abgrenzung, Quellen, Invarianten und Abhängigkeiten. Die Features stehen als Abschnitte in der Epic-Datei. [BACKLOG.md](BACKLOG.md) ist die zentrale Übersicht, [ROADMAP.md](ROADMAP.md) ordnet Features den Meilensteinen zu, [TRACEABILITY.md](TRACEABILITY.md) belegt, dass jeder Abschnitt der Konzeptdokumente abgedeckt ist.

## Identifikatoren

Epics heißen `E00` bis `E99`, Features `F-<Epic>.<Nummer>`, etwa `F-07.03`. Offene Entscheidungen heißen `OD-<Nummer>` und stehen in [OPEN_DECISIONS.md](../decisions/OPEN_DECISIONS.md). Eine ID wird nie neu vergeben. Ein verworfenes Feature behält seine ID und erhält den Status `dropped` mit Begründung.

## Status

| Status | Bedeutung |
| --- | --- |
| `todo` | Erfasst, aber noch nicht bereit. Abhängigkeiten oder Entscheidungen sind offen. |
| `ready` | Definition of Ready erfüllt. Darf gezogen werden. |
| `in-progress` | Ein Bearbeiter arbeitet daran. Das Feld „Bearbeiter“ ist gesetzt. |
| `review` | Umsetzung fertig, Prüfung durch Mensch oder unabhängigen Reviewer offen. |
| `done` | Definition of Done erfüllt, Nachweise eingetragen. |
| `blocked` | Begonnen, aber durch eine Entscheidung, ein externes Problem oder ein anderes Feature aufgehalten. Der Grund steht im Feature. |
| `dropped` | Bewusst verworfen. Die Begründung steht im Feature. |

Ein Epic ist `done`, wenn alle Features `done` oder `dropped` sind. Ein Epic ist `in-progress`, sobald eines seiner Features begonnen wurde.

## Priorität und Meilenstein

P0 ist für den jeweiligen Meilenstein zwingend, P1 wichtig und verschiebbar, P2 optional oder langfristig. Die Meilensteine M1 bis M6 sind in [ROADMAP.md](ROADMAP.md) beschrieben. Ein Feature mit späterem Meilenstein wird erst gezogen, wenn die P0-Features des laufenden Meilensteins erledigt oder blockiert sind.

## Feature-Format

```markdown
### F-07.03 Titel

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.02, OD-04
- Quelle: ARCH §6.4, UI §10.2
- Bearbeiter: offen · Nachweise: offen

Ein bis drei Sätze, die Zweck und Umfang beschreiben.

- [ ] Prüfbares Akzeptanzkriterium
```

Nach Abschluss stehen unter „Nachweise“ Commit-Hash, ausgeführte Tests und gegebenenfalls Benchmark-IDs. Die Übersichtstabelle am Anfang jeder Epic-Datei wird beim Statuswechsel mitgepflegt.

## Definition of Ready

Ein Feature ist `ready`, wenn alle Abhängigkeiten `done` sind, keine verknüpfte offene Entscheidung (OD) mehr offen ist und die Akzeptanzkriterien so formuliert sind, dass ein Test oder eine Prüfung sie belegen kann.

## Definition of Done

Ein Feature ist `done`, wenn jedes Akzeptanzkriterium abgehakt ist und dafür ein ausgeführter Nachweis vorliegt. Formatter, Linter und Tests sind gelaufen, und das Ergebnis steht unter „Nachweise“. Betroffene Dokumentation ist aktualisiert. Die Übersicht in der Epic-Datei und der Fortschritt in [BACKLOG.md](BACKLOG.md) sind nachgezogen. Die Änderung ist als Conventional Commit auf `develop` festgehalten. Ein Push erfordert eine eigene Freigabe des Benutzers.

## Ablauf für einen Agenten

1. In [BACKLOG.md](BACKLOG.md) den Abschnitt „Now“ lesen.
2. Ein Feature mit Status `ready` wählen, dessen Abhängigkeiten `done` sind. P0 geht vor P1.
3. Status auf `in-progress` setzen, Bearbeiter eintragen und diese Änderung zuerst committen oder im selben Commit mitführen.
4. Die Quellabschnitte in `docs/research/` lesen. Das Feature ist die Arbeitsanweisung, die Quelle liefert den fachlichen Hintergrund.
5. Umsetzen, testen, Nachweise eintragen, Status auf `review` oder `done` setzen.
6. Abhängige Features prüfen. Sind deren Abhängigkeiten nun erfüllt, werden sie auf `ready` gesetzt.

Ein Agent bearbeitet genau ein Feature. Er startet keine weiteren Agenten pro Datei oder Befund. Teilaufgaben, die beim Arbeiten auffallen, werden als neues Feature mit Status `todo` angelegt und nicht still mit umgesetzt. Eine fachliche Frage, die der Agent nicht aus Code und Quelle beantworten kann, wird als OD-Eintrag erfasst, und das Feature wird `blocked`.

## Fachliche Invarianten

Diese Regeln gelten für jedes Feature, unabhängig vom Epic. Sie stammen aus ARCH §4.2, §6.3, §13 und UI §1.3, §4.4.

| Invariante | Bedeutung |
| --- | --- |
| Small Trusted Core | Mathematische Gültigkeit entscheidet der formale Prüfer, nie ein Sprachmodell. |
| Kein `VERIFIED` ohne Prüfnachweis | Nur das Verifikations-Backend setzt `VERIFIED` bzw. `FORMALLY_VERIFIED`. Agentenaussagen und UI-Aktionen können es nicht. |
| Immutable Target | Der Hash der formalen Zielaussage ändert sich nach Bestätigung nicht. |
| Append-only Events | Ereignisse werden nie geändert oder gelöscht. Korrekturen sind neue Ereignisse. |
| Evidenz ist kein Beweis | Numerische und symbolische Ergebnisse bleiben in ihrer Erkenntnisstufe, bis sie formal geprüft sind. |
| Blind Rediscovery | In `BLIND_REDISCOVERY` hat kein Agent Zugriff auf Referenzlösungen. |
| Keine Historienmutation | Eingriffe erzeugen neue Versuche, Branches oder Runs. Bestehende Verläufe bleiben unverändert. |
| Getrennte Statusräume | Agentenstatus, Erkenntnisstufe und Verifikationsstatus sind getrennte Typen (siehe [glossary.md](../glossary.md)). |

## Pflege von Entscheidungen

Eine offene Entscheidung wird in [OPEN_DECISIONS.md](../decisions/OPEN_DECISIONS.md) mit Optionen und betroffenen Features geführt. Ist sie getroffen, entsteht ein ADR nach [adr-template.md](../decisions/adr-template.md), der OD-Eintrag verweist darauf, und die blockierten Features werden geprüft.

## Neue Anforderungen

Eine neue Anforderung bekommt die nächste freie Feature-ID im passenden Epic. Passt sie in kein Epic, entsteht ein neues Epic aus [templates/epic-template.md](templates/epic-template.md). Danach werden [BACKLOG.md](BACKLOG.md), [ROADMAP.md](ROADMAP.md) und, falls sie aus einer Quelle stammt, [TRACEABILITY.md](TRACEABILITY.md) ergänzt.
