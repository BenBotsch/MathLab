// Client of the versioned MathLab API (F-14.01). Types mirror docs/reference/openapi-v1.json;
// api.test.ts checks them against that document, so a schema change cannot pass unnoticed.

export const API_PREFIX = "/api/v1";

export type RunStatus =
  | "RUNNING"
  | "PAUSED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface RunSummary {
  run_id: string;
  status: RunStatus;
  last_sequence: number;
  pause_reason?: string | null;
}

export interface RunList {
  runs: RunSummary[];
}

/** Error body of the API (`ApiError`); `error` is the error type, e.g. `UNAVAILABLE`. */
export class ApiRequestError extends Error {
  constructor(
    readonly status: number,
    readonly error: string,
    message: string,
  ) {
    super(message);
  }
}

export async function listRuns(
  fetchFn: typeof fetch = fetch,
): Promise<RunList> {
  const response = await fetchFn(`${API_PREFIX}/runs`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    let error = "HTTP_ERROR";
    let message = `GET /runs failed with ${response.status}`;
    try {
      const body = (await response.json()) as {
        error?: string;
        message?: string;
      };
      error = body.error ?? error;
      message = body.message ?? message;
    } catch {
      // The body is not JSON, e.g. a proxy error page; keep the generic message.
    }
    throw new ApiRequestError(response.status, error, message);
  }
  return (await response.json()) as RunList;
}
