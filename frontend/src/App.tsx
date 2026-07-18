import { useEffect, useState } from "react";
import { fetchCase, runAnalysis } from "./api";
import { FindingsPanel } from "./components/FindingsPanel";
import { ActionLedger } from "./components/ActionLedger";
import { InferredPanel } from "./components/InferredPanel";
import type { AnalysisResult, MissingField, TranscriptLine } from "./types";

export default function App() {
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [gaps, setGaps] = useState<MissingField[]>([]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCase()
      .then((c) => {
        setTranscript(c.transcript);
        setGaps(c.completeness);
      })
      .catch((e) => setError(String(e)));
  }, []);

  async function analyze() {
    setLoading(true);
    setError(null);
    try {
      setResult(await runAnalysis());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app__head">
        <h1>Tumor Board — Gap Detection</h1>
        <button onClick={analyze} disabled={loading}>
          {loading ? "Analyzing…" : "Run analysis"}
        </button>
      </header>

      {error && <div className="error">{error}</div>}

      <div className="layout">
        <section className="panel transcript">
          <h2>Transcript</h2>
          {transcript.map((l) => (
            <p key={l.line} className="tline">
              <span className="tline__meta">
                {l.timestamp} · {l.speaker}
              </span>
              {l.text}
            </p>
          ))}
        </section>

        <div className="findings-col">
          {gaps.length > 0 && (
            <section className="panel">
              <h2>Structural gaps ({gaps.length})</h2>
              <p className="empty">Oncology essentials absent from the structured case:</p>
              <ul className="gaps">
                {gaps.map((g) => (
                  <li key={g.field}>
                    <code>{g.field}</code> — {g.reason}
                  </li>
                ))}
              </ul>
            </section>
          )}
          <FindingsPanel findings={result?.findings ?? []} />
          {result?.enrichment && <InferredPanel enrichment={result.enrichment} />}
          <ActionLedger items={result?.action_ledger ?? []} />
        </div>
      </div>
    </div>
  );
}
