import type { AnalysisResult, CaseDetail, CaseResponse, CaseSummary } from "./types";

// Vite proxies /api -> http://localhost:8000 (see vite.config.ts).
const BASE = "/api";

export async function fetchCase(): Promise<CaseResponse> {
  const res = await fetch(`${BASE}/case`);
  if (!res.ok) throw new Error(`GET /case failed: ${res.status}`);
  return res.json();
}

export async function runAnalysis(caseId: string): Promise<AnalysisResult> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: caseId }), // analyze the selected data/cases patient
  });
  if (!res.ok) {
    // surface the backend's reason (e.g. missing API key) instead of just the code
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch { /* noop */ }
    throw new Error(`POST /analyze failed: ${res.status}${detail ? ` — ${detail}` : ""}`);
  }
  return res.json();
}

export async function fetchCases(): Promise<CaseSummary[]> {
  const res = await fetch(`${BASE}/cases`);
  if (!res.ok) throw new Error(`GET /cases failed: ${res.status}`);
  return res.json();
}

export async function fetchCaseDetail(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${BASE}/cases/${encodeURIComponent(caseId)}`);
  if (!res.ok) throw new Error(`GET /cases/${caseId} failed: ${res.status}`);
  return res.json();
}
