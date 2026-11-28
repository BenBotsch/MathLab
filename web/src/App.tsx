import { useEffect, useState } from "react";
import { ApiRequestError, listRuns, type RunList } from "./api";

type State =
  | { kind: "loading" }
  | { kind: "loaded"; runs: RunList["runs"] }
  | { kind: "failed"; message: string };

/** Minimal shell for F-15.01: loads the run list from the server and shows it unchanged. */
export function App({ fetchFn = fetch }: { fetchFn?: typeof fetch }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    listRuns(fetchFn).then(
      (list) => active && setState({ kind: "loaded", runs: list.runs }),
      (err: unknown) => {
        const message =
          err instanceof ApiRequestError
            ? `${err.error}: ${err.message}`
            : "Backend nicht erreichbar";
        if (active) setState({ kind: "failed", message });
      },
    );
    return () => {
      active = false;
    };
  }, [fetchFn]);

  return (
    <main>
      <h1>MathLab</h1>
      <h2>Runs</h2>
      {state.kind === "loading" && <p>Lade Runs …</p>}
      {state.kind === "failed" && <p role="alert">{state.message}</p>}
      {state.kind === "loaded" && state.runs.length === 0 && (
        <p>Keine Runs vorhanden.</p>
      )}
      {state.kind === "loaded" && state.runs.length > 0 && (
        <table>
          <thead>
            <tr>
              <th scope="col">Run</th>
              <th scope="col">Status</th>
              <th scope="col">Letzte Sequenz</th>
            </tr>
          </thead>
          <tbody>
            {state.runs.map((run) => (
              <tr key={run.run_id}>
                <td>
                  <code>{run.run_id}</code>
                </td>
                <td>{run.status}</td>
                <td>{run.last_sequence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
