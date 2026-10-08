import { useState } from "react";
import { api } from "../api";
import { TierPill } from "./ui";

export function DedupPanel({ report, onResolve }) {
  const [busy, setBusy] = useState(null);
  if (!report) return null;

  const groups = report.groups || [];

  const resolve = async (id, e) => {
    e.stopPropagation();
    setBusy(id);
    try {
      await api.resolve(id);
      onResolve && onResolve();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-white">
          Duplicate Clusters{" "}
          <span className="ml-1 rounded bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber-300">
            {groups.length}
          </span>
        </div>
        <span className="text-[11px] text-slate-500">
          Grouped by normalized domain + fuzzy company name
        </span>
      </div>

      {groups.map((g) => {
        const p = g.primary;
        return (
          <div key={g.group_id} className="rounded-xl border border-edge bg-panel/40 p-4">
            <div className="flex items-center gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-white">{p.company}</span>
                  <TierPill tier={p.tier} />
                </div>
                <div className="text-xs text-slate-500">
                  {p.domain} · {p.completeness_score.toFixed(0)}% complete ·{" "}
                  {p.owner_email || "no email"}
                </div>
              </div>
              <span className="rounded bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-300">
                KEEP
              </span>
            </div>

            {g.duplicates.map((d) => (
              <div
                key={d.id}
                className="mt-2 flex items-center justify-between gap-3 rounded-lg border border-dashed border-edge bg-white/[0.02] px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-slate-300">{d.company}</div>
                  <div className="truncate text-[11px] text-slate-500">
                    99% match: {d.domain} · {d.sources?.map((s) => s.source).join(", ") || "import"}
                    {" · "}
                    <span className="text-amber-300/80">{d.email_status === "verified" ? "emails verified" : d.email_status} · flagged</span>
                  </div>
                </div>
                <button
                  onClick={(e) => resolve(p.id, e)}
                  disabled={busy === p.id}
                  className="shrink-0 rounded-md bg-rose-500/15 px-2.5 py-1.5 text-[11px] font-medium text-rose-300 ring-1 ring-rose-400/30 hover:bg-rose-500/25 disabled:opacity-50"
                >
                  {busy === p.id ? "Removing…" : "Insert dup"}
                </button>
              </div>
            ))}
          </div>
        );
      })}

      {groups.length === 0 && (
        <div className="rounded-xl border border-edge bg-panel/40 p-10 text-center text-sm text-slate-500">
          No duplicates found.
        </div>
      )}
    </div>
  );
}