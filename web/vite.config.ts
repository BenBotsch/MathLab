/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The client talks to the local FastAPI backend only through the versioned API (ADR-0001).
// In development Vite forwards /api to it, so the browser sees one origin and needs no CORS.
const backend = process.env["MATHLAB_API_URL"] ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": backend } },
  test: { environment: "jsdom" },
});
