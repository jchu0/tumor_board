import type { ActionItem } from "../types";

// A separate artifact from the findings feed (README §5): a human to-do list,
// generated once at end-of-meeting, not another live finding.
export function ActionLedger({ items }: { items: ActionItem[] }) {
  if (items.length === 0) return null;
  return (
    <section className="panel">
      <h2>Action ledger ({items.length})</h2>
      <table className="ledger">
        <thead>
          <tr>
            <th>Action</th>
            <th>Owner</th>
            <th>Deadline</th>
            <th>Linked finding</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a, i) => (
            <tr key={i}>
              <td>{a.action}</td>
              <td>{a.owner}</td>
              <td>{a.deadline ?? "—"}</td>
              <td>{a.linked_finding ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
