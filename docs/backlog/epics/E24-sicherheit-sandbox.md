# E24 Sicherheit, Sandbox und Risikoregister

- Status: `todo` · Meilenstein: M1, Ausbau M2 und M3
- Quellen: ARCH §3.2 (Sicherheit), §6.4, §21, §21.1; UI §16.2, §18.3
- Abhängige Epics: E00, E04, E05, E07, E14

## Ziel

Generierter Code läuft isoliert, Werkzeuge und Menschen haben nur die nötigen Rechte, Secrets und personenbezogene Daten bleiben geschützt, und jedes Risiko aus ARCH §21 hat eine überprüfbare Gegenmaßnahme.

## Abgrenzung

Die fachlichen Schutzmaßnahmen wie Axiomreport, Statement Fidelity und Leakage-Kontrollen liegen in ihren Fach-Epics. F-24.09 verweist auf sie.

## Invarianten

Die UI mutiert die Datenbank nie direkt. Externe Paper- und Tooldaten sind nicht vertrauenswürdig. Keine Secrets in Eventlogs, Modellprompts oder UI-Artefakten (UI §18.3).

## Übersicht

| Feature | Titel | Status | Priorität | Meilenstein |
| --- | --- | --- | --- | --- |
| F-24.01 | Container-Sandbox für generierten Code | `todo` | P0 | M1 |
| F-24.02 | Toolrechte pro Agentenrolle | `todo` | P0 | M1 |
| F-24.03 | Rollen und Berechtigungen | `todo` | P0 | M1 |
| F-24.04 | Secrets und `privacy_classification` | `todo` | P0 | M1 |
| F-24.05 | Externe Daten als nicht vertrauenswürdig | `todo` | P1 | M3 |
| F-24.06 | Ressourcenquoten und Early Stopping | `todo` | P0 | M1 |
| F-24.07 | Keine direkte Datenbankmutation durch die UI | `todo` | P0 | M1 |
| F-24.08 | CI-Gates für Provenienz und Sicherheit | `todo` | P1 | M2 |
| F-24.09 | Risikoregister | `ready` | P0 | M1 |

## Features

### F-24.01 Container-Sandbox für generierten Code

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-00.04
- Quelle: ARCH §21 (gefährlicher generierter Code), §6.4; UI §18.3
- Bearbeiter: offen · Nachweise: offen

Generierter Python-, Lean- und Simulationscode läuft in einem Container ohne Netzwerk, mit Ressourcenlimits für CPU, Speicher und Zeit und ohne Zugriff auf Secrets oder das Host-Dateisystem außerhalb eines Arbeitsverzeichnisses.

- [ ] Ein Test zeigt, dass Code in der Sandbox weder Netzwerk noch Host-Dateien erreicht.
- [ ] Ein Endlosschleifen-Test wird nach dem Zeitlimit beendet und als Fehlerklasse erfasst.

### F-24.02 Toolrechte pro Agentenrolle

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-01.04
- Quelle: ARCH §6.4; UI §7.3 (Toolrechte), §18.3
- Bearbeiter: offen · Nachweise: offen

Jede Agentenrolle hat eine explizite Liste erlaubter Werkzeuge und Parameter. Nicht erlaubte Aufrufe werden abgelehnt und protokolliert.

- [ ] Ein Tactic Generator kann keinen Verifikationsstatus schreiben.

### F-24.03 Rollen und Berechtigungen

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.01
- Quelle: UI §18.3 (Start, Stop, Budgetänderung, Toolrechte), §2.1 (System Configuration)
- Bearbeiter: offen · Nachweise: offen

Rollenmodell für Menschen mit Rechten für Start, Stop, Budgetänderung, Toolrechte und Konfiguration. In M1 genügt ein lokales Einbenutzer-Profil mit derselben Prüfung im Code.

- [ ] Jedes Kommando durchläuft die Rechteprüfung, auch im Einbenutzerbetrieb.

### F-24.04 Secrets und `privacy_classification`

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-02.01
- Quelle: UI §16.2, §18.3
- Bearbeiter: offen · Nachweise: offen

Secrets kommen nur aus Umgebung oder Secret Store und erscheinen nie in Events, Prompts, Logs oder Artefakten. Jedes Event trägt `privacy_classification`, die steuert, was an externe Modelle oder Tracing-Dienste gehen darf.

- [ ] Ein Secret-Scanner läuft in CI.
- [ ] Events mit vertraulicher Klassifizierung werden nicht an externe Dienste exportiert (Test).

### F-24.05 Externe Daten als nicht vertrauenswürdig

- Status: `todo` · Priorität: P1 · Meilenstein: M3
- Abhängigkeiten: F-10.04
- Quelle: UI §18.3; ARCH §21 (halluzinierte Quellen, falsche Memory)
- Bearbeiter: offen · Nachweise: offen

Inhalte aus Papers, Datensätzen und Toolausgaben werden als Daten behandelt, nie als Anweisungen an Agenten. Sie erhalten die niedrigste Vertrauensebene, bis sie geprüft sind.

- [ ] Ein Test mit eingebetteter Anweisung in einem importierten Paper ändert das Agentenverhalten nicht.

### F-24.06 Ressourcenquoten und Early Stopping

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-08.04, F-23.05
- Quelle: ARCH §21 (unkontrollierte Rechenkosten); UI §18.3 (Ressourcenverbrauch durch Benutzeraktionen)
- Bearbeiter: offen · Nachweise: offen

Quoten für Token, Kosten, Zeit und Rechenzeit pro Run, Agent und Benutzer mit Early Stopping bei Überschreitung.

- [ ] Ein Run, der seine Kostenquote erreicht, stoppt mit eigenem Status und Event.

### F-24.07 Keine direkte Datenbankmutation durch die UI

- Status: `todo` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: F-14.04
- Quelle: UI §18.3
- Bearbeiter: offen · Nachweise: offen

Der Client hat keine Datenbankzugangsdaten. Schreibzugriffe laufen ausschließlich über die Control API.

- [ ] Die Client-Konfiguration enthält keine Datenbankverbindung (CI-Prüfung).

### F-24.08 CI-Gates für Provenienz und Sicherheit

- Status: `todo` · Priorität: P1 · Meilenstein: M2
- Abhängigkeiten: F-00.06, F-24.04
- Quelle: ARCH §21.1 (letzte zwei Gates)
- Bearbeiter: offen · Nachweise: offen

CI prüft Datensatz-, Modell- und Experiment-Provenienz sowie ausführbare Agentenartefakte und externe Abhängigkeiten auf Sicherheitsprobleme.

- [ ] Ein Artefakt ohne Provenienzangabe lässt das Gate fehlschlagen.
- [ ] Abhängigkeiten werden auf bekannte Schwachstellen geprüft.

### F-24.09 Risikoregister

- Status: `ready` · Priorität: P0 · Meilenstein: M1
- Abhängigkeiten: keine
- Quelle: ARCH §21
- Bearbeiter: offen · Nachweise: offen

Die 13 Risiken aus ARCH §21 sind auf Features abgebildet. Ein Risiko gilt als behandelt, wenn alle zugeordneten Features `done` sind.

| Risiko | Gegenmaßnahme laut ARCH | Features |
| --- | --- | --- |
| Falsche Übersetzung natürlicher Mathematik | Zwei Formalisierungen oder menschliches Review, semantischer Audit | F-03.04, F-03.05, F-20.11 |
| Trivial korrektes, aber falsches Ziel | Unveränderliches Originalproblem, Statement-Fidelity-Prüfung | F-01.03, F-03.05, F-04.04 |
| Versteckte `sorry`- und Axiomabhängigkeiten | Axiomreport und zusätzliche Checker | F-04.05, F-04.06 |
| Halluzinierte Quellen und Lemmata | ID-basierte Quelle und exakte Bibliotheksreferenz | F-01.05, F-13.03 |
| Numerische Evidenz als Beweis | Strikte Statusmaschine | F-01.01, F-01.07 |
| Reward Hacking und Scheinfortschritt | Harte Verifikationsgates, mehrdimensionale Evaluation | F-12.04, F-12.05, F-09.07 |
| Selbstverstärkende falsche Memory | Evidenzstatus, Provenienz, Validierung, Quarantäne | F-10.04, F-10.08 |
| Train- und Test-Leakage | Blind-Holdouts, Varianten, Versionierung | F-11.08, F-03.08 |
| Unkontrollierte Rechenkosten | Tool-Limits, Quoten, Scheduling, Early Stopping | F-08.04, F-24.06 |
| Gefährlicher generierter Code | Container-Sandbox, begrenzte Rechte, Ressourcenlimits | F-24.01, F-24.02 |
| Modellregression durch Continual Learning | Golden Benchmarks und Freigabeprozess | F-12.11, F-12.13 |
| Inkonsistente Ergebnisse verschiedener Toolversionen | Environment- und Artefakt-Fingerprints | F-00.03, F-04.09 |
| Unterschiedliche Softwarelizenzen | Lizenzinventar und Redistribution-Review | F-00.07 |

- [ ] Jedes Risiko hat mindestens ein Feature mit einem Akzeptanzkriterium, das die Gegenmaßnahme prüft.
- [ ] Das Register wird bei jedem Meilenstein-Abschluss überprüft.
