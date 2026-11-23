# ADR-0006 Artefaktspeicher

- Status: `accepted`
- Datum: 2026-11-23
- Löst: OD-06
- Betroffene Features: F-02.07

## Kontext

ARCH §17.1 und §17.2 sehen für Lean-Beweisdateien, Solverlogs, Simulationen und Grafiken zuerst das Dateisystem und später S3-kompatiblen Speicher vor. ARCH §18.4 verlangt Hashes von `(statement, proof, toolchain, dependencies)` für Caching und Reproduzierbarkeit. Da Events append-only sind, darf ein referenziertes Artefakt nicht verändert werden.

## Optionen

| Option | Vorteile | Nachteile |
| --- | --- | --- |
| A: Content-addressed Dateisystem auf dem Host, per Bind-Mount im Container | Einfach, die Artefakte lassen sich direkt ansehen und sind leicht zu sichern. Unveränderlichkeit ergibt sich aus dem Hash. | Bind-Mounts unter Windows sind langsamer, und die Rechte müssen beachtet werden. |
| B: Wie A, aber in einem Docker-Volume | Schnellere I/O im Container | Schwerer einzusehen und zu sichern, und die Daten sind an Docker gebunden. |
| C: S3-kompatibel (z. B. MinIO) sofort | Später ohne Umstellung | Zusätzlicher Dienst ohne Nutzen in M1 |

## Empfehlung

Option A hinter einer schmalen Schnittstelle `ArtifactStore` (`put(bytes, media_type) -> ArtifactRef`, `get(ref)`, `exists(ref)`), sodass ein S3-Backend später austauschbar ist.

- **Namensschema:** `sha256/<ersten 2 Hexzeichen>/<vollständiger Hash>`. Die Metadaten (Medientyp, Größe, Erzeugungszeit, Provenienz) liegen in der Datenbank, nicht im Dateinamen.
- **Schreiben:** atomar in eine temporäre Datei mit anschließendem Umbenennen. Ein vorhandener Hash wird nicht überschrieben, damit ist das Schreiben idempotent.
- **Aufbewahrung:** In M1 wird nichts gelöscht. Später entfernt eine Garbage Collection nur Artefakte, auf die kein Event verweist, und nur nach ausdrücklicher Bestätigung.
- **Ablageort:** ein konfigurierbares Datenverzeichnis außerhalb des Repositorys, z. B. `MATHLAB_DATA_DIR/artifacts`. Den Standardpfad und eine Sicherung legt der Benutzer fest.

## Entscheidung

Angenommen am 2026-11-23: Option A wie empfohlen. Der Standardpfad des Datenordners ist `D:\MathLabData`, überschreibbar über `MATHLAB_DATA_DIR`. Artefakte liegen unter `D:\MathLabData\artifacts`. Der Datenordner wird nach `D:\Sicherungen\MathLab` gesichert. Die Sicherung ist ein eigenes Feature (F-00.09).

## Folgen

F-02.07 wird `ready`, sobald F-01.02 `done` ist. Die Event-Payloads verweisen über `ArtifactRef` (Hash) auf die Artefakte, nie über Pfade. Es bleibt das Risiko, dass der Speicher ohne Garbage Collection wächst. Für M1 ist das bewusst in Kauf genommen.
