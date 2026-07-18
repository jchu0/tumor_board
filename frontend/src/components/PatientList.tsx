import type { CaseSummary } from "../types";

export function PatientList({
  cases,
  selected,
  onSelect,
}: {
  cases: CaseSummary[];
  selected: string | null;
  onSelect: (caseId: string) => void;
}) {
  return (
    <aside className="patients">
      <h2 className="patients__head">Patients</h2>
      <ul className="patients__list">
        {cases.map((c) => {
          // patient_ref is "Name, DOB ... (age n)" — the name alone is the label.
          const name = c.patient_ref?.split(",")[0] ?? c.case_id;
          return (
            <li key={c.case_id}>
              <button
                className={`patients__item ${selected === c.case_id ? "patients__item--on" : ""}`}
                onClick={() => onSelect(c.case_id)}
              >
                <span className="patients__name">{name}</span>
                <span className="patients__meta">
                  {c.cancer_type ?? "—"} · {c.document_count} docs
                </span>
                <span className="patients__id">{c.case_id}</span>
              </button>
            </li>
          );
        })}
        {!cases.length && <li className="empty">No cases found in data/cases/.</li>}
      </ul>
    </aside>
  );
}
