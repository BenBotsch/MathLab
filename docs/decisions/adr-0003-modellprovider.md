# ADR-0003 Modellprovider und lokale Modelle

- Status: `accepted`
- Datum: 2026-11-23
- Löst: OD-03
- Betroffene Features: F-07.01, F-07.04, F-07.16, F-12.10

## Kontext

ARCH §17.3 geht von einer NVIDIA Quadro RTX 4000 mit 8 GB VRAM aus. Es empfiehlt kleine lokale Proof-Modelle, realistische Benchmarks zu Quantisierung und Kontextfenstern, große Modelle über austauschbare Provider und vorerst kein Fine-Tuning großer Modelle. Die Adapter-Schicht F-07.01 bleibt providerneutral. Nach der Small-Trusted-Core-Invariante entscheidet kein Modell über die Gültigkeit eines Beweises.

Der Benutzer nutzt Claude ausschließlich über eine Subscription und hat keinen API-Zugang. Er will das Projekt lokal mit Claude Code Desktop bedienen und ausführen.

## Optionen

| Option | Vorteile | Nachteile |
| --- | --- | --- |
| A: Ein externer Provider über eine API für den Proof-Agenten | Volle Kontrolle über Modell, Parameter und Kosten pro Aufruf | Entfällt, weil kein API-Zugang besteht. |
| B: Nur lokal (kleines Proof-Modell, quantisiert, 8 GB VRAM) | Keine laufenden Kosten, offline und reproduzierbar | Bei 8 GB VRAM sind nur kleine oder stark quantisierte Modelle möglich, mit deutlich geringerer Erfolgsquote. |
| C: Claude über die Subscription, auf zwei Wegen: interaktiv aus Claude Code Desktop und unbeaufsichtigt über die Claude-Code-CLI im Headless-Modus | Keine zusätzlichen Kosten außer der Subscription. Bedienung aus der gewohnten Umgebung. | Es gelten die Rate-Limits der Subscription, und Token und Kosten lassen sich nur eingeschränkt messen. Ob automatisierte Nutzung zulässig ist, richtet sich nach den Nutzungsbedingungen. |

## Entscheidung

Angenommen am 2026-11-23: Option C.

1. **Interaktiver Betrieb.** MathLab stellt seine Funktionen als Werkzeuge bereit, die Claude Code Desktop aufruft: als MCP-Server und als CLI (neues Feature F-07.16). Darüber startet Claude Code Runs, schlägt Taktiken vor und liest Ergebnisse. Claude Code ist dabei ein Agent wie jeder andere. Seine Vorschläge gehen an das Verifikations-Backend. Es kann keinen Status `VERIFIED` setzen und die Zielaussage nicht ändern.
2. **Unbeaufsichtigter Betrieb.** Für Benchmarkläufe ruft der Model Adapter (F-07.01) `claude -p --output-format json --model <id>` als Subprozess auf. Ein API-Schlüssel wird nicht verwendet.
3. **Limits statt Kostenbudget.** Pro Run gelten harte Grenzen für die Zahl der Modellaufrufe, die Tokens (soweit die CLI sie meldet) und die Laufzeit. Der Runner setzt sie durch und protokolliert sie. Ein USD-Budget entfällt.
4. **Reproduzierbarkeit.** Modell-ID, CLI-Version und Parameter werden in jedem Run fixiert und in der Provenienz (F-01.05) gespeichert.
5. **Lokale Modelle** werden in M1 nicht eingesetzt. Ihre Bewertung bleibt bei F-12.10.

Ob die Nutzungsbedingungen der Subscription diese automatisierte Nutzung abdecken, prüft der Benutzer.

## Folgen

F-07.01 bekommt den CLI-Adapter als erstes reales Modell. Kosten werden dort als „nicht gemessen“ geführt, nicht als 0. F-07.16 wird neu angelegt. Benchmarks mit vielen Aufgaben laufen langsamer und können am Rate-Limit abbrechen. Der Runner muss solche Abbrüche als eigenen Fehlertyp führen und fortsetzbar machen. Es bleibt das Risiko, dass sich das Verhalten der CLI zwischen Versionen ändert. Deshalb wird die CLI-Version gepinnt und protokolliert.
