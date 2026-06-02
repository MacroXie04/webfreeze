import type { FreezeReport } from "../api";

export function JsFidelityReport({ report }: { report: FreezeReport | null }) {
  if (!report || report.widgets.length === 0) return null;
  return (
    <div className="fidelity">
      <strong>Converted widgets</strong>
      <ul>
        {report.widgets.map((w, i) => (
          <li key={i}>
            <code>{w.selector}</code> · {w.type} → {w.strategy} <span className="fidelity__note">({w.note})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
