# ADR-0007 Golden-Problemliste für M1

- Status: `accepted`
- Datum: 2026-11-24
- Löst: OD-07
- Betroffene Features: F-11.01, F-11.03, F-11.04, F-03.02

## Kontext

ARCH §19 verlangt für Phase 1 20 bis 50 Aufgaben aus einer fixierten Benchmarkliste, und jede Aufgabe braucht einen unveränderlichen Zielhash. ARCH §16.2 teilt die Golden-Test-Suite in sechs Level, M1 verwendet Level 1 bis 3. ARCH §16.4 verlangt, dass Referenzlösungen für Blind Rediscovery vor den Agenten verborgen bleiben und dass Testfälle samt Formalisierung versioniert werden. ARCH §22 Schritt 2 nennt eine fixierte kleine Problemkollektion mit formalen Zielaussagen. Das Referenzbeispiel aus ARCH §15 ist Pflicht.

## Optionen

| Option | Vorteile | Nachteile |
| --- | --- | --- |
| A: Eigene Aufgaben der Level 1 bis 3 | Formulierung und Lizenz liegen beim Projekt. Die Lean-Aussagen sind passend zur gepinnten Mathlib geschrieben, und die Level sind gezielt gestreut. | Nicht direkt mit veröffentlichten Ergebnissen vergleichbar. Die Aufgaben sind Standardresultate, deren Beweise Modelle aus dem Training kennen können. |
| B: Auswahl aus miniF2F | Etablierter Vergleichsmaßstab (ARCH §16.1) | Die Lean-4-Fassungen müssen an die gepinnte Mathlib angepasst werden, die Lizenz jedes Ports ist zu prüfen, und die Aufgaben sind oft schwerer als Level 3. Die Datenkontamination ist bekannt hoch. |
| C: Mischung aus A und B | Eigener Kern plus externer Vergleich | Doppelter Aufwand bereits in M1 |

## Empfehlung

Option A für M1, miniF2F als Ergänzung ab M2 mit einem neuen Listenstand.

Der Entwurf liegt unter `benchmarks/golden/m1/v1/tasks.json` und umfasst 24 Aufgaben:

| Level | Aufgaben | Methodenhinweise |
| --- | --- | --- |
| 1 | g01 bis g07 | algebraische Umformung, Ungleichung, Fallunterscheidung |
| 2 | g08 bis g16 | Induktion, Teilbarkeit; g08 ist das Referenzbeispiel aus ARCH §15 |
| 3 | g17 bis g24 | Ungleichung, Teleskopsumme, Widerspruch, Induktion, Fallunterscheidung, Kombinatorik |

- **Holdout:** g05, g10, g14, g18, g21 und g23, je eine Aufgabe pro Methode und alle drei Level. Ihre Referenzlösungen liegen getrennt unter `benchmarks/golden/m1/holdout-references/`. Für alle anderen Aufgaben ist keine Referenzlösung abgelegt.
- **Lizenz:** `own-work`. Die Aufgaben sind eigene Formulierungen mathematischer Standardresultate.
- **Zielhash:** nach F-01.03 über Lean-Aussage, Import `Mathlib` und die Toolchain aus `lean/lean-toolchain`.
- **Unveränderlichkeit:** Eine geänderte Aufgabe ergibt einen neuen Listenstand `v2`. `v1` wird nicht umgeschrieben.

Spezialtests aus ARCH §16.2, etwa falsche Aussagen, fehlende Voraussetzungen oder mehrdeutige Texte, gehören nicht in diese Liste. Sie brauchen ein erwartetes Ergebnis wie „widerlegt“ und kommen mit eigenen Features.

## Entscheidung

Angenommen am 2026-11-25: Option A wie empfohlen, mit dem Listenstand `v1` aus 24 Aufgaben und der Holdout-Auswahl g05, g10, g14, g18, g21 und g23.

## Folgen

Mit der Annahme wird F-11.01 `done`. F-11.03 und F-11.04 sind dann nicht mehr durch OD-07 blockiert, und F-03.02 kann `ready` werden. Es bleibt das Risiko, dass Standardresultate im Training der Modelle vorkommen. Für den Vergleich von Strategien in M1 ist das hinnehmbar, für Aussagen über eigenständiges Entdecken nicht.
