import type { AnalysisResult, CaseResponse } from "./types";

// Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
const BASE = "/api";

export async function fetchCase(): Promise<CaseResponse> {
  const res = await fetch(`${BASE}/case`);
  if (!res.ok) throw new Error(`GET /case failed: ${res.status}`);
  return res.json();
}

export async function runAnalysis(): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}), // empty body → backend uses the bundled synthetic case
  });
  if (!res.ok) throw new Error(`POST /analyze failed: ${res.status}`);
  return res.json();
}
