import type { Finding } from "../types";
import { FindingCard } from "./FindingCard";

export function FindingsPanel({ findings }: { findings: Finding[] }) {
  if (findings.length === 0) {
    return <p className="empty">No findings yet — run the analysis.</p>;
  }
  return (
    <section className="panel">
      <h2>Findings ({findings.length})</h2>
      {findings.map((f, i) => (
        <FindingCard key={i} f={f} index={i + 1} />
      ))}
    </section>
  );
}
