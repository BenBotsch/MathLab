# Entscheidungen

Architekturentscheidungen werden als ADR (Architecture Decision Record) festgehalten. Offene Fragen, die noch nicht entschieden sind, stehen in [OPEN_DECISIONS.md](OPEN_DECISIONS.md).

## Ablauf

Eine offene Frage bekommt einen Eintrag `OD-<Nummer>` mit Kontext, Optionen und den Features, die sie blockiert. Ein Agent darf Optionen ausarbeiten und eine Empfehlung begründen. Die Entscheidung selbst trifft der Benutzer. Danach entsteht eine Datei `adr-<Nummer>-<kurzname>.md` nach [adr-template.md](adr-template.md), der OD-Eintrag erhält den Status `decided` mit Verweis auf den ADR, und die blockierten Features werden nach [WORKFLOW.md](../backlog/WORKFLOW.md) neu bewertet.

Ein ADR wird nicht nachträglich umgeschrieben. Ändert sich eine Entscheidung, entsteht ein neuer ADR, der den alten mit `superseded` markiert.

## Verzeichnis

| ADR | Titel | Status |
| --- | --- | --- |
| (noch keine) | | |
