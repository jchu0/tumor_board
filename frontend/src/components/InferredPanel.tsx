import type { Enrichment } from "../types";

// Inferred context is a DISTINCT channel from grounded findings — dashed border,
// "inferred" styling — and every item shows the verbatim source quote it points at.
export function InferredPanel({ enrichment }: { enrichment: Enrichment }) {
  const { inferred, skipped_reason } = enrichment;
  if (skipped_reason && inferred.length === 0) {
    return (
      <section className="panel">
        <h2>Inferred context</h2>
        <p className="empty">Agent did not run: {skipped_reason}</p>
      </section>
    );
  }
  if (inferred.length === 0) return null;

  return (
    <section className="panel">
      <h2>Inferred context ({inferred.length})</h2>
      <p className="empty">Nuance read from the prose — unconfirmed, each cited to its source.</p>
      {inferred.map((o, i) => (
        <article key={i} className="inferred">
          <header className="inferred__head">
            <span className="badge badge--kind">{o.kind}</span>
            <span className="badge badge--match">conf {Math.round(o.confidence * 100)}%</span>
            {o.raises_check && <span className="badge badge--op-not_confirmed">raises {o.raises_check}</span>}
          </header>
          <p className="inferred__summary">{o.summary}{o.value ? ` — ${o.value}` : ""}</p>
          <blockquote className="inferred__quote">
            “{o.source.quote}”
            <cite>
              {o.source.location}
              {o.source.line !== null ? ` · line ${o.source.line}` : ""}
              {o.source.speaker ? ` · ${o.source.speaker}` : ""}
            </cite>
          </blockquote>
        </article>
      ))}
    </section>
  );
}
