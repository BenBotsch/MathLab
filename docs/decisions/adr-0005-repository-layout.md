# ADR-0005 Repository-Layout und Build-Werkzeuge

- Status: `accepted`
- Datum: 2026-11-23
- Löst: OD-05
- Betroffene Features: F-00.02, F-00.03, F-00.05, F-15.01

## Kontext

ARCH §18.3 zeigt einen Zielbaum mit `apps/`, `services/`, `packages/`, `engines/`, `knowledge/`, `ml/` und `benchmarks/`. Es empfiehlt außerdem, zu Beginn eine modularisierte gemeinsame Codebasis zu führen und Komponenten erst bei klaren API-Grenzen auszulagern. F-00.02 legt nur an, was M1 braucht.

## Optionen

**Python-Paketverwaltung**

| Option | Bewertung |
| --- | --- |
| uv mit `uv.lock` und Workspaces | Schnell, plattformübergreifendes Lockfile, verwaltet auch die Python-Version. Mehrere Pakete in einem Monorepo sind über Workspaces möglich. |
| Poetry | Ausgereift, aber langsamer und mit schwächerer Workspace-Unterstützung |
| pip-tools | Minimal, aber ohne Workspaces und ohne Verwaltung der Python-Version |

**Layout**

| Option | Bewertung |
| --- | --- |
| Ein Python-Paket `mathlab` mit Unterpaketen (etwa `core`, `events`, `verification`, `api`) | Entspricht der Empfehlung einer gemeinsamen Codebasis. Die Modulgrenzen werden per Import-Linter geprüft. |
| Vollständiger Baum aus ARCH §18.3 von Anfang an | Leere Verzeichnisse und Paketgrenzen ohne konkreten Bedarf |

## Empfehlung

- **Python** 3.12 als Minimum, gepinnt über `.python-version`. Eine neuere Version ist möglich, wenn alle Engines (Lean-Anbindung, SymPy, Z3) sie unterstützen. Das prüft F-00.03.
- **Paketverwaltung** uv mit `uv.lock`. Ruff übernimmt Formatter und Linter, mypy die Typprüfung, pytest die Tests.
- **Frontend** (nach ADR-0001) mit pnpm und Lockfile, TypeScript strict und Vite.
- **Layout in M1:**

```text
MathLab/
├── src/mathlab/          # ein Python-Paket, Unterpakete nach Komponenten
│   ├── core/             # Domänenmodell, Contracts (E01)
│   ├── events/           # Event Store (E02)
│   ├── verification/     # Lean-Anbindung (E04)
│   └── api/              # FastAPI (E14)
├── tests/
├── web/                  # Frontend (E15), nur bei Option A/B aus ADR-0001
├── lean/                 # Lean-Projekt mit lakefile und lean-toolchain
├── benchmarks/golden/    # Golden-Probleme (F-11.01)
├── configs/
├── docs/
└── .github/workflows/
```

Unterpakete entstehen erst mit dem Feature, das sie braucht. Eine Aufteilung in mehrere Pakete über uv-Workspaces folgt erst, wenn eine reale API-Grenze besteht.

## Entscheidung

Angenommen am 2026-11-23: wie empfohlen. Python ab 3.12, uv mit `uv.lock`, ruff, mypy und pytest, ein Paket `src/mathlab/`, Frontend mit pnpm und Vite.

## Folgen

Danach kann F-00.02 `ready` werden. F-00.03 pinnt Python, uv, Lean und Mathlib. F-00.05 baut die CI auf `uv run ruff`, `mypy` und `pytest` auf. Es bleibt das Risiko, dass ein einzelnes Paket später schwer zu teilen ist. Import-Regeln zwischen den Unterpaketen begrenzen dieses Risiko.
