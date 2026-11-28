import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

const run = (id: string, status: string, last: number) => ({
  run_id: id,
  status,
  last_sequence: last,
  pause_reason: null,
});

function respond(body: unknown, status = 200): typeof fetch {
  return async () => new Response(JSON.stringify(body), { status });
}

afterEach(cleanup);

describe("App", () => {
  it("shows the runs from GET /runs", async () => {
    const fetchFn = respond({
      runs: [run("a1", "RUNNING", 7), run("b2", "COMPLETED", 12)],
    });
    render(<App fetchFn={fetchFn} />);
    expect(await screen.findByText("a1")).toBeTruthy();
    expect(screen.getByText("COMPLETED")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
  });

  it("says when there are no runs", async () => {
    render(<App fetchFn={respond({ runs: [] })} />);
    expect(await screen.findByText("Keine Runs vorhanden.")).toBeTruthy();
  });

  it("shows the API error instead of an empty list", async () => {
    render(
      <App fetchFn={respond({ error: "UNAVAILABLE", message: "down" }, 503)} />,
    );
    expect((await screen.findByRole("alert")).textContent).toBe(
      "UNAVAILABLE: down",
    );
  });

  it("reports an unreachable backend", async () => {
    const fetchFn: typeof fetch = async () => {
      throw new TypeError("fetch failed");
    };
    render(<App fetchFn={fetchFn} />);
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Backend nicht erreichbar",
    );
  });
});
