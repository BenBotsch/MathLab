# E00 Projektfundament

- Status: `todo` · Meilenstein: M1, Ausbau M2
- Quellen: ARCH §3.2, §17, §18.3, §21.1, §22; UI §19
- Abhängige Epics: keine. Alle anderen Epics bauen hierauf auf.

## Ziel

Ein reproduzierbares Repository, in dem Toolchain, Abhängigkeiten und Umgebungen fixiert sind und jede Änderung durch CI-Gates läuft. Die Entscheidungen zu Plattform, Layout und Werkzeugen sind getroffen, bevor Code entsteht.

## Abgrenzung

Fachliche Sicherheitsmaßnahmen wie Sandbox und Toolrechte liegen in E24. Lean-spezifische Einrichtung liegt in E04.

## Invarianten

Versionen von Python, Lean, Mathlib, Solvern und Bibliotheken sind gepinnt (ARCH §3.2, UI §19.2). Jeder Run kann seinen Environment-Fingerprint nennen.

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-00.01 | Architekturentscheidungen für M1 vorbereiten | `ready` | P0 | M1 |
| F-00.02 | Repository-Grundgerüst | `todo` | P0 | M1 |
| F-00.03 | Toolchain-Pinning und Environment-Fingerprint | `todo` | P0 | M1 |
| F-00.04 | Container-Umgebung | `todo` | P0 | M1 |
| F-00.05 | CI-Grundgates | `todo` | P0 | M1 |
| F-00.06 | Fachliche CI-Gates | `todo` | P1 | M2 |
| F-00.07 | Lizenzinventar | `todo` | P1 | M1 |
| F-00.08 | Entwickler-Setup dokumentieren | `todo` | P1 | M1 |

## Features

### F-00.01 Architekturentscheidungen für M1 vorbereiten

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: keine
- Quelle: ARCH §17.1, §17.3, §18.3; UI §19
- Bearbeiter: offen · Nachweise: offen

Für OD-01 bis OD-06 werden Optionen recherchiert, verglichen und als ADR-Entwurf mit Empfehlung vorgelegt. Die Entscheidung trifft der Benutzer.

- [ ] Für jede OD-01 bis OD-06 liegt ein ADR-Entwurf mit Optionen, Empfehlung und Begründung vor.
- [ ] Der Widerspruch Flutter gegen React (OD-01) ist mit beiden Quellen belegt dargestellt.
- [ ] Nach Freigabe durch den Benutzer sind die ADRs `accepted` und die OD-Einträge `decided`.

### F-00.02 Repository-Grundgerüst

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.01 (OD-05)
- Quelle: ARCH §18.3
- Bearbeiter: offen · Nachweise: offen

Verzeichnisstruktur nach dem gewählten Layout anlegen, nur mit den Teilen, die M1 braucht. Python-Paket mit Paketverwaltung, Lockfile und Testgerüst.

- [ ] Struktur entspricht dem ADR zu OD-05.
- [ ] Ein leerer Test läuft lokal mit einem dokumentierten Befehl.
- [ ] `.gitignore` deckt Build-Artefakte, Umgebungen und lokale Daten ab.

Referenzbeispiel aus ARCH §18.3, unverändert zitiert. Bei Abweichung gilt die Quelle. Der Baum ist das Zielbild. Maßgeblich ist das ADR zu OD-05, und in M1 entstehen nur die benötigten Teile.

```text
math-research-system/
├── apps/
│   ├── desktop/
│   ├── web/
│   └── cli/
├── services/
│   ├── api/
│   ├── orchestration/
│   ├── verification/
│   ├── experiment-tracking/
│   └── knowledge/
├── packages/
│   ├── core/
│   │   ├── problems/
│   │   ├── statements/
│   │   ├── proofs/
│   │   └── contracts/
│   ├── agents/
│   ├── strategies/
│   ├── search/
│   ├── metrics/
│   └── model-adapters/
├── engines/
│   ├── lean4/
│   ├── symbolic/
│   ├── numerical/
│   ├── smt/
│   └── simulation/
├── knowledge/
│   ├── graph/
│   ├── retrieval/
│   ├── embeddings/
│   └── memory/
├── ml/
│   ├── datasets/
│   ├── training/
│   ├── evaluation/
│   └── models/
├── benchmarks/
│   ├── golden/
│   ├── minif2f/
│   ├── proofnet/
│   └── custom/
├── experiments/
├── docs/
├── configs/
├── scripts/
└── .github/
```

### F-00.03 Toolchain-Pinning und Environment-Fingerprint

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02
- Quelle: ARCH §3.2, §9.2, §21 (Toolversionen); UI §19.2
- Bearbeiter: offen · Nachweise: offen

Alle Versionen werden fixiert, und eine Funktion erzeugt einen Fingerprint aus Python-, Lean-, Mathlib-, Solver- und Bibliotheksversionen sowie Git-Commit. Der Fingerprint wird später in jedem ProofAttempt gespeichert (F-09.02).

- [ ] Lockfiles für Python und, falls vorhanden, Frontend sind eingecheckt.
- [ ] Der Fingerprint ist deterministisch und ändert sich bei jeder Versionsänderung.
- [ ] Ein Test belegt beide Eigenschaften.

### F-00.04 Container-Umgebung

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.03
- Quelle: ARCH §3.2 (Portabilität), §17.1 (Docker)
- Bearbeiter: offen · Nachweise: offen

Container für Backend, PostgreSQL und Engines (Lean, SymPy). Lokal unter Windows und Linux startbar.

- [ ] Ein Befehl startet Backend und Datenbank.
- [ ] Lean und Mathlib laufen im Container mit der gepinnten Version.
- [ ] Start unter Windows ist belegt.

### F-00.05 CI-Grundgates

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.02
- Quelle: ARCH §21.1, §17.1 (GitHub Actions)
- Bearbeiter: offen · Nachweise: offen

CI prüft Formatierung, Linting, statische Typprüfung und Tests bei jedem Push.

- [ ] Workflow läuft und schlägt bei einem absichtlichen Formatfehler fehl.
- [ ] Typprüfung ist für das Core-Paket im strikten Modus aktiv.

### F-00.06 Fachliche CI-Gates

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-00.05, F-02.01, F-04.05, F-11.03
- Quelle: ARCH §21.1
- Bearbeiter: offen · Nachweise: offen

CI erweitert um reproduzierbare Lean-Testbeweise mit fixierter Mathlib, das Verbot von `sorry` und unerlaubten Axiomen in freigegebenen Beweisartefakten, Schema-Kompatibilität der Events und Engines, Golden-Smoke-Tests mit kleinem Budget, Simulationstests mit fixierten Seeds und sichtbare Regressionen bei Erfolgsquote und Kosten.

- [ ] Ein Beweisartefakt mit `sorry` lässt den CI-Lauf fehlschlagen.
- [ ] Eine inkompatible Schemaänderung lässt den CI-Lauf fehlschlagen.
- [ ] Golden-Smoke läuft unter einem festen Zeitlimit und berichtet Erfolgsquote und Kosten.

### F-00.07 Lizenzinventar

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: keine
- Quelle: ARCH §17.3 (Lizenzprüfung), §21 (Risiko Lizenzen)
- Bearbeiter: offen · Nachweise: offen

Inventar der Lizenzen aller eingesetzten Werkzeuge, Bibliotheken, Modellgewichte und Datensätze mit Vermerk zur Weitergabe.

- [ ] Datei `docs/licenses.md` listet jede Komponente mit Lizenz und Quelle.
- [ ] Neue Abhängigkeiten werden im Inventar ergänzt (Regel in AGENTS.md).

### F-00.08 Entwickler-Setup dokumentieren

- Status: `todo` · Priorität: P1 · Meilenstein: M1
- Abhängigkeiten: F-00.04
- Quelle: ARCH §3.2
- Bearbeiter: offen · Nachweise: offen

Root-README mit Zweck, Setup unter Windows und Linux, Teststart und Verweis auf die Docs.

- [ ] Ein frisches Klonen und Befolgen der README führt zu grünen Tests.
