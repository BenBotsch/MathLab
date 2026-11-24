# Golden-Problemliste M1

Fixierte Aufgabenliste für Meilenstein M1 (ARCH §16.2, §19 Phase 1; F-11.01, ADR-0007).

| Pfad | Inhalt |
| --- | --- |
| `v1/tasks.json` | Listenstand 1 mit 24 Aufgaben der Level 1 bis 3 |
| `holdout-references/` | Referenzlösungen der Holdout-Aufgaben, getrennt von der Liste |

Ein Listenstand wird nicht geändert. Eine Korrektur erzeugt einen neuen Stand `v2`.

`mathlab.golden.load_golden` prüft die Liste: Umfang, Level, eindeutige IDs, Zielhashes, das Referenzbeispiel aus ARCH §15 und die getrennt abgelegten Referenzlösungen. `tests/test_golden.py` kompiliert alle Aussagen mit `sorry` gegen die gepinnte Mathlib, wenn `MATHLAB_TEST_LEAN_IMAGE` gesetzt ist.

Agenten im Modus `BLIND_REDISCOVERY` dürfen `holdout-references/` nicht lesen. Die Durchsetzung folgt mit F-11.02.
