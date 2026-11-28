// @vitest-environment node
// Reads the committed OpenAPI document from disk, so it runs in Node instead of jsdom.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { API_PREFIX, ApiRequestError, listRuns, type RunStatus } from "./api";

const openapi = JSON.parse(
  readFileSync(
    new URL("../../docs/reference/openapi-v1.json", import.meta.url),
    "utf8",
  ),
) as {
  paths: Record<string, unknown>;
  components: {
    schemas: Record<
      string,
      { properties?: Record<string, unknown>; enum?: string[] }
    >;
  };
};

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function json(body: unknown, status = 200): typeof fetch {
  return async () => response(body, status);
}

describe("contract with openapi-v1.json", () => {
  it("knows the run list path and fields", () => {
    expect(Object.keys(openapi.paths)).toContain(`${API_PREFIX}/runs`);
    const summary = openapi.components.schemas["RunSummary"]?.properties ?? {};
    expect(Object.keys(summary).sort()).toEqual(
      ["last_sequence", "pause_reason", "run_id", "status"].sort(),
    );
    const statuses: RunStatus[] = [
      "RUNNING",
      "PAUSED",
      "COMPLETED",
      "FAILED",
      "CANCELLED",
    ];
    expect(openapi.components.schemas["RunStatus"]?.enum?.sort()).toEqual(
      statuses.sort(),
    );
  });
});

describe("listRuns", () => {
  it("requests GET /api/v1/runs and returns the list", async () => {
    let url = "";
    const fetchFn: typeof fetch = async (input) => {
      url = String(input);
      return response({ runs: [] });
    };
    expect(await listRuns(fetchFn)).toEqual({ runs: [] });
    expect(url).toBe("/api/v1/runs");
  });

  it("turns an API error body into ApiRequestError", async () => {
    const error = await listRuns(
      json(
        { error: "UNAVAILABLE", message: "read backend not configured" },
        503,
      ),
    ).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiRequestError);
    expect(error).toMatchObject({ status: 503, error: "UNAVAILABLE" });
  });

  it("keeps a generic message when the error body is not JSON", async () => {
    const fetchFn: typeof fetch = async () =>
      new Response("Bad Gateway", { status: 502 });
    await expect(listRuns(fetchFn)).rejects.toMatchObject({
      status: 502,
      error: "HTTP_ERROR",
    });
  });
});
