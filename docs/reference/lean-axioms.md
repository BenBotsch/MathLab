# Erlaubte Axiome der Lean-Prüfung

Diese Seite beschreibt, welche Axiome ein von `LeanChecker` (`src/mathlab/engines/lean_check.py`) geprüfter Beweis verwenden darf. Grundlage sind ARCH §7.3 (Schritt 2), §13.2 und §21 sowie Feature F-04.05.

## Erlaubt

Die Voreinstellung `AxiomPolicy()` erlaubt genau die drei Axiome der Standardgrundlage von Lean (`STANDARD_AXIOMS`):

| Axiom | Bedeutung |
| --- | --- |
| `propext` | Propositionale Extensionalität |
| `Classical.choice` | Auswahlaxiom, Grundlage der klassischen Logik in Lean |
| `Quot.sound` | Gleichheit im Quotiententyp, liefert Funktionsextensionalität |

Eine andere Menge wird über `AxiomPolicy(allowed=...)` beim Erzeugen von `LeanChecker` gesetzt. Eine Abweichung von der Voreinstellung muss auf dieser Seite dokumentiert werden.

## Abgelehnt

Jedes Axiom außerhalb der erlaubten Menge führt zur Ablehnung. Der `AxiomReport` nennt das Axiom und ordnet es einer dieser Gruppen zu:

| Gruppe | Feld | Beispiele |
| --- | --- | --- |
| Unvollständiger Beweis | `sorry` | `sorryAx`, entsteht durch `sorry` |
| Zusätzliches Vertrauen | `extra_trust` | `Lean.ofReduceBool`, `Lean.trustCompiler` und die Hilfsaxiome `<name>._native.…` von `native_decide` |
| Eigene Axiome | `custom` | jede mit `axiom` deklarierte Aussage, etwa `axiom bad : False` |

Mechanismen mit zusätzlichem Vertrauen lassen den Kern kompiliertem Code vertrauen. Sie stehen deshalb im Report und werden nicht stillschweigend akzeptiert (ARCH §13.2).

## Ermittlung

Nach dem Beweis hängt der Prüfer zwei Befehle an:

```lean
#eval IO.println "MATHLAB-AXIOMS-<zufällige uuid>"
#print axioms _root_.<theorem>
```

Gewertet wird nur die Ausgabe nach dem letzten Vorkommen der zufälligen Markierung. Ein Beweis kann deshalb keinen gefälschten Report ausgeben. `_root_` verhindert, dass ein im Beweis geöffneter `namespace` den Namen auf ein anderes Theorem umlenkt. Der gemeldete Name muss dem Theorem aus `lean_code` entsprechen. Fehlt der Report oder passt der Name nicht, gilt der Beweis als abgelehnt („axiom report missing“).

`lean_code` muss mit `theorem <name>` beginnen, sonst endet die Prüfung mit `SYNTAX_ERROR`.
