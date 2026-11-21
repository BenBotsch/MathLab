# Glossar und Statusräume

Das System führt mehrere Statusräume, die nie vermischt werden dürfen (UI §1.3). Ein Agent kann technisch erfolgreich enden, während seine Vermutung falsch ist. Ein Simulationsergebnis ist kein Beweis. Jeder Statusraum ist deshalb ein eigener Typ im Code und eine eigene Anzeige in der Oberfläche.

## Erkenntnisstufe einer mathematischen Aussage

Quelle: ARCH §1.2. Diese Stufe beschreibt, was über eine Aussage behauptet werden darf.

| Status | Bedeutung | Zulässige Behauptung |
| --- | --- | --- |
| `CONJECTURED` | Eine Vermutung wurde formuliert. | Die Aussage ist möglicherweise wahr. |
| `NUMERICALLY_SUPPORTED` | Experimente stützen die Aussage. | Für die getesteten Fälle liegen passende Beobachtungen vor. |
| `SYMBOLICALLY_DERIVED` | Eine symbolische Engine hat eine Herleitung erzeugt. | Eine algebraische Ableitung liegt vor. Ihre Vertrauensbasis ist noch zu prüfen. |
| `PARTIALLY_PROVEN` | Teile wurden formal bewiesen. | Einzelne Beweispflichten sind gültig, andere offen. |
| `FORMALLY_VERIFIED` | Der vertrauenswürdige Prüfer hat die festgelegte formale Aussage bewiesen. | Ein formaler Beweis existiert relativ zu Logik, Definitionen und Axiomen. |
| `REFUTED` | Ein gültiges Gegenbeispiel oder eine formale Widerlegung liegt vor. | Die Aussage ist in ihrem Geltungsbereich falsch. |
| `UNRESOLVED` | Bisher unentschieden. | Es gibt keinen belastbaren Abschluss. |

`FORMALLY_VERIFIED` setzt ausschließlich das Verifikations-Backend (E04). Kein Agent und keine UI-Aktion kann diesen Status setzen.

## Verifikationsstatus

Ergebnis eines vertrauenswürdigen Proof Checkers für ein konkretes Artefakt (UI §1.3). Werte sind `VERIFIED`, `OPEN` und `REJECTED`. Ist der Verifier nicht erreichbar, bleibt der Status `OPEN` mit dem Vermerk „unterbrochen“ (UI §18.2).

## Agentenstatus

Technischer Prozesszustand eines Agenten oder Tasks, etwa laufend, fertig, fehlgeschlagen, pausiert oder abgebrochen. Er sagt nichts über mathematische Gültigkeit.

## Run-Status

Zustand eines Forschungsruns (UI §3.2) mit den Werten `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED` und `CANCELLED`. Ein Wechsel gilt erst, wenn das Backend ihn bestätigt hat (UI §10.2).

## Status eines Proof-Knotens

Anzeige im Proof Search Graph (UI §4.3). Farbe ist nie die einzige Information, jeder Status trägt Label und Icon.

| Status | Farbe/Icon | Bedeutung |
| --- | --- | --- |
| `VERIFIED` | Grün, Häkchen | Ein vertrauenswürdiger Prüfer hat das Ziel akzeptiert. |
| `RUNNING` | Blau, Spinner | Ein Agent arbeitet an diesem Teilziel. |
| `WAITING` | Gelb, Uhr | Wartet auf Voraussetzungen oder Ressourcen. |
| `FAILED` | Rot, Kreuz | Ein konkreter Versuch ist gescheitert. |
| `CONJECTURED` | Violett, Glühbirne | Noch unbewiesene Hypothese. |
| `ABANDONED` | Grau, Archiv | Suchzweig bewusst beendet. |
| `REFUTED` | Dunkelrot, Gegenbeispiel | Zielaussage ist widerlegt. |

## Betriebsmodi eines Runs

Quelle: ARCH §3.3.

| Modus | Beschreibung | Kritische Grenze |
| --- | --- | --- |
| `BLIND_REDISCOVERY` | Bekanntes Problem ohne Referenzlösung bearbeiten. | Referenzbeweis und Lösung bleiben verborgen. |
| `ASSISTED_REDISCOVERY` | Bekannte Hilfssätze dürfen gesucht werden. | Genutzte Ressourcen werden vollständig protokolliert. |
| `ALTERNATIVE_PROOF` | Weitere Beweise derselben Aussage finden. | Unterschiedliche Texte sind nicht zwingend unterschiedliche Methoden. |
| `CONJECTURE_RESEARCH` | Vermutungen formulieren, prüfen oder widerlegen. | Empirische Evidenz bleibt von Beweisen getrennt. |
| `MATHEMATICAL_EXPLORATION` | Berechnungen, Simulationen, Mustersuche. | Ergebnisse sind zunächst experimentelle Befunde. |

## Vertrauensebenen im Wissensgraphen

Quelle: ARCH §11.2. Eine Kante ist entweder formal verifiziert oder abgeleitet, unverifiziert aber plausibel (agentische Hypothese) oder nur statistisch ähnlich. Statistische Ähnlichkeit wird nie automatisch als mathematische Äquivalenz gelesen.

## Begriffe

| Begriff | Bedeutung |
| --- | --- |
| AMRS | Artificial Mathematical Research System, Arbeitstitel des Gesamtsystems. |
| Control Center | Die Forschungsoberfläche aus dem UI-Konzept. |
| Ziel-Hash | Hash der unveränderlichen formalen Zielaussage eines Problems (ARCH §13.2). |
| Proof Attempt | Ein protokollierter Beweisversuch mit Modell, Strategie, Ressourcen und Ergebnis (ARCH §9.1). |
| Beweispflicht | Ein formales Teilziel, das bewiesen werden muss. |
| Premise | Ein Hilfssatz, der für einen Beweisschritt herangezogen wird. |
| Golden Task | Fest versionierte Benchmarkaufgabe mit bekanntem Ergebnis (ARCH §16.2). |
| ARCH, UI | Kurzbezeichnung der beiden Konzeptdokumente in `docs/research/`. `ARCH §9.3` verweist auf Abschnitt 9.3 des Architekturkonzepts. |
