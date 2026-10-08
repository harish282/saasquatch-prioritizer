import { api } from "../api";
import { Badge, ScoreBar, TierPill } from "./ui";

const SORTABLE = {
  company: "Company",
  employees: "Size",
  priority_score: "Priority",
  icp_score: "ICP",
  confidence_score: "Confidence",
  revenue_estimate_usd: "Revenue",
};

export function LeadTable({ leads, sort, onSort, onOpen, filters, onResolve }) {
  const emailTone = { verified: "verified", risky: "risky", invalid: "invalid", missing: "missing", unknown: "unknown", none: "missing" };
  const phoneTone = { verified: "verified", risky: "risky", invalid: "invalid", missing: "missing", unknown: "unknown" };

  const exportUrl = api.exportUrl({
    q: filters.q,
    country: filters.country,
    industry: filters.industry,
    tier: filters.tier,
    min_score: filters.min_score,
    has_email: filters.has_email,
  });

  const HeaderCell = ({ id }) => (
    <th
      onClick={() => onSort(id)}
      className="cursor-pointer select-none px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400 hover:text-teal-300"
    >
      {SORTABLE[id] || id}
      {sort.field === id && <span className="ml-1 text-teal-400">{sort.order === "desc" ? "↓" : "↑"}</span>}
    </th>
  );

  return (
    <div className="overflow-hidden rounded-xl border border-edge bg-panel/40">
      <div className="flex items-center justify-between border-b border-edge px-4 py-3">
        <div className="text-sm font-semibold text-white">Lead Queue</div>
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span>{leads.length} results</span>
          <a
            href={exportUrl}
            className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:bg-blue-500"
          >
            Export CSV
          </a>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="border-b border-edge bg-white/[0.03]">
            <tr>
              <HeaderCell id="company" />
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Industry</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Location</th>
              <HeaderCell id="employees" />
              <HeaderCell id="revenue_estimate_usd" />
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Contact</th>
              <HeaderCell id="icp_score" />
              <HeaderCell id="confidence_score" />
              <HeaderCell id="priority_score" />
              <th className="px-4 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-slate-400">Tier</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr
                key={l.id}
                onClick={() => onOpen(l)}
                className="cursor-pointer border-b border-edge/50 last:border-0 hover:bg-white/[0.03]"
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-100">{l.company}</div>
                  <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                    <span className="truncate">{l.domain}</span>
                    {!l.is_primary && l.duplicate_of_id && (
                      <Badge label="dup" tone="info" />
                    )}
                    {l.dedup_group && !l.is_primary && (
                      <span
                        className="cursor-pointer text-amber-300/90 hover:underline"
                        onClick={(e) => {
                          e.stopPropagation();
                          onResolve(l.id);
                        }}
                      >
                        resolve
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-slate-300">{l.industry || "—"}</td>
                <td className="px-4 py-3 text-xs text-slate-400">
                  {l.city ? `${l.city}, ` : ""}
                  {l.country || "—"}
                </td>
                <td className="px-4 py-3 text-xs tabular-nums text-slate-300">
                  {l.employees ?? "—"}
                </td>
                <td className="px-4 py-3 text-xs tabular-nums text-slate-300">
                  {l.revenue_estimate_usd
                    ? `$${(l.revenue_estimate_usd / 1e6).toFixed(1)}M`
                    : "—"}
                </td>
                <td className="px-4 py-3">
                  <div className="text-xs text-slate-300">{l.owner_name || "—"}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-1">
                    <Badge
                      label={l.email_status_label || l.email_status}
                      tone={emailTone[l.email_status] || "unknown"}
                    />
                    {(l.owner_phone || l.company_phone) && (
                      <Badge label={l.phone_status} tone={phoneTone[l.phone_status] || "unknown"} />
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <ScoreBar value={l.icp_score} color="bg-sky-400" />
                </td>
                <td className="px-4 py-3">
                  <ScoreBar value={l.confidence_score} color="bg-emerald-400" />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold tabular-nums text-white">
                      {l.priority_score.toFixed(0)}
                    </span>
                    <ScoreBar value={l.priority_score} color="bg-teal-400" />
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <TierPill tier={l.tier} />
                </td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td colSpan={10} className="px-4 py-12 text-center text-sm text-slate-500">
                  No leads match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}