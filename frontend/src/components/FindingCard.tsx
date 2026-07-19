import type { Finding } from "../types";

// Scannable scaffold: each finding collapses to a one-line summary (issue + the
// key badges) so the whole list reads at a glance, and expands to the full detail
// (recommendation, patient note, live question, evidence) on click. Native
// <details>/<summary> — accessible, no extra state.
export function FindingCard({ f, index }: { f: Finding; index: number }) {
  const notConfirmed = f.operability_status === "not_confirmed";
  return (
    <details className={`finding ${notConfirmed ? "finding--warn" : ""}`}>
      <summary className="finding__summary">
        <span className="finding__num">{index}</span>
        <span className="finding__issue">{f.issue}</span>
        <span className="finding__badges">
          {f.recommendation_grade && (
            <span className="badge badge--grade" title="Class of Recommendation / Level of Evidence">
              {f.recommendation_grade}
            </span>
          )}
          {/* Only the deterministic safety warning — a surgical option the operability
              check did NOT clear. "cleared" and the (non-deterministic) match% are dropped. */}
          {f.operability_status === "not_confirmed" && (
            <span className="badge badge--op-not_confirmed">operability not confirmed</span>
          )}
        </span>
      </summary>

      <div className="finding__detail">
        <p className="finding__source">{f.source_agent}</p>
        <p className="finding__rec">{f.recommendation}</p>
        <p className="finding__patient">
          <strong>To address with the patient:</strong> {f.patient_facing_note}
        </p>
        <div className="finding__live">
          <strong>Live question:</strong> {f.live_question}
        </div>
        <footer className="finding__foot">
          <span>evidence: {f.evidence_ref}</span>
          <span>rationale: {f.rationale_status.replace("_", " ")}</span>
          {f.transcript_ref && (
            <span>
              {f.transcript_ref.line !== null
                ? `line ${f.transcript_ref.line}`
                : "absence (not discussed)"}
              {f.transcript_ref.speaker ? ` · ${f.transcript_ref.speaker}` : ""}
            </span>
          )}
        </footer>
      </div>
    </details>
  );
}
