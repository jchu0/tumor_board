import type { Finding } from "../types";

// The two axes are shown SEPARATELY on purpose (README §5): evidence strength
// vs. our confidence we matched it to the right patient.
export function FindingCard({ f }: { f: Finding }) {
  const notConfirmed = f.operability_status === "not_confirmed";
  return (
    <article className={`finding ${notConfirmed ? "finding--warn" : ""}`}>
      <header className="finding__head">
        <span className="finding__source">{f.source_agent}</span>
        {f.recommendation_grade && (
          <span className="badge badge--grade" title="Class of Recommendation / Level of Evidence">
            {f.recommendation_grade}
          </span>
        )}
        <span className="badge badge--match" title="Confidence this evidence fits THIS patient">
          match {Math.round(f.match_confidence * 100)}%
        </span>
        {f.operability_status !== "not_applicable" && (
          <span className={`badge badge--op badge--op-${f.operability_status}`}>
            operability: {f.operability_status.replace("_", " ")}
          </span>
        )}
      </header>

      <h3 className="finding__issue">{f.issue}</h3>
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
    </article>
  );
}
