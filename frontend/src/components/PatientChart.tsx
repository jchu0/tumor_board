import { useEffect, useState } from "react";
import { Markdown } from "./Markdown";
import type { CaseDetail } from "../types";

const TRANSCRIPT_TAB = "__transcript__";

/**
 * One patient's chart: a tab per specialty folder that actually exists on disk,
 * plus the board transcript. Folders vary by case (variant_4 carries pneumology,
 * variant_3 has no laboratory) — the tab strip reflects what is there rather than
 * a fixed set with empty placeholders.
 */
export function PatientChart({ detail }: { detail: CaseDetail }) {
  const [tab, setTab] = useState<string>(detail.folders[0]?.name ?? TRANSCRIPT_TAB);
  const [docId, setDocId] = useState<string | null>(null);

  // Reset to the first tab whenever the selected patient changes, otherwise the
  // previous patient's tab can point at a folder this one does not have.
  useEffect(() => {
    setTab(detail.folders[0]?.name ?? TRANSCRIPT_TAB);
    setDocId(null);
  }, [detail.case_id]);

  const folder = detail.folders.find((f) => f.name === tab);
  const documents = folder?.documents ?? [];
  const active = documents.find((d) => d.doc_id === docId) ?? documents[0];

  return (
    <section className="chart">
      <header className="chart__head">
        <div>
          <h2>{detail.patient_ref ?? detail.case_id}</h2>
          <p className="chart__sub">
            {detail.cancer_type && <span className="pill">{detail.cancer_type}</span>}
            {detail.board_date && <span>Board {detail.board_date}</span>}
            <span>{detail.document_count} documents</span>
          </p>
          {detail.line_of_therapy && <p className="chart__line">{detail.line_of_therapy}</p>}
        </div>
      </header>

      <nav className="tabs" role="tablist">
        {detail.folders.map((f) => (
          <button
            key={f.name}
            role="tab"
            aria-selected={tab === f.name}
            className={`tab ${tab === f.name ? "tab--on" : ""}`}
            onClick={() => {
              setTab(f.name);
              setDocId(null);
            }}
          >
            {f.label}
            <span className="tab__count">{f.documents.length}</span>
          </button>
        ))}
        {detail.transcript && (
          <button
            role="tab"
            aria-selected={tab === TRANSCRIPT_TAB}
            className={`tab tab--transcript ${tab === TRANSCRIPT_TAB ? "tab--on" : ""}`}
            onClick={() => setTab(TRANSCRIPT_TAB)}
          >
            Board transcript
          </button>
        )}
      </nav>

      {tab === TRANSCRIPT_TAB ? (
        <div className="doc doc--solo">
          <Markdown source={detail.transcript ?? ""} />
        </div>
      ) : (
        <div className="folder">
          <ul className="doclist">
            {documents.map((d) => (
              <li key={d.doc_id}>
                <button
                  className={`doclist__item ${active?.doc_id === d.doc_id ? "doclist__item--on" : ""}`}
                  onClick={() => setDocId(d.doc_id)}
                >
                  <span className="doclist__date">{d.date ?? "standing"}</span>
                  <span className="doclist__title">{d.title}</span>
                </button>
              </li>
            ))}
            {!documents.length && <li className="empty">No documents in this folder.</li>}
          </ul>
          <div className="doc">
            {active ? <Markdown source={active.body} /> : <p className="empty">Nothing to show.</p>}
          </div>
        </div>
      )}
    </section>
  );
}
