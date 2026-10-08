import { Badge, Field, ScoreBar, TierPill } from "./ui";

function Group({ title, children }) {
  return (
    <div className="rounded-xl border border-edge bg-white/[0.02] p-3">
      <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-teal-300/90">
        {title}
      </div>
      {children}
    </div>
  );
}

export function ScoreDrawer({ lead, onClose }) {
  if (!lead) return null;
  const sb = lead.score_breakdown || {};
  const icp = sb.icp || {};
  const comp = sb.completeness || {};
  const conf = sb.confidence || {};
  const valid = lead.validation_detail || {};
  const sources = lead.sources || [];

  const tierDot = {
    hot: "bg-emerald-400",
    warm: "bg-amber-400",
    cold: "bg-slate-500",
  }[lead.tier];

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-edge bg-[#151c2e] shadow-2xl">
        <div className="sticky top-0 flex items-start gap-3 border-b border-edge bg-[#151c2e]/95 p-5 backdrop-blur">
          <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-sky-500 text-sm font-black text-slate-900">
            {lead.company.charAt(0)}
          </div>
          <div className="min-w-0">
            <div className="truncate text-base font-semibold text-white">{lead.company}</div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>
                {lead.city ? `${lead.city}, ` : ""}
                {lead.country || "—"}
              </span>
              <span>·</span>
              <span>{lead.industry || "—"}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-auto rounded-md text-slate-500 hover:bg-white/10 hover:text-white"
            aria-label="Close"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex flex-col gap-3 p-5">
          <div className="flex items-center justify-between rounded-xl border border-edge bg-panel/70 p-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-bold tabular-nums text-white">
                  {lead.priority_score.toFixed(0)}
                </span>
                <TierPill tier={lead.tier} />
              </div>
              <div className="mt-0.5 text-xs text-slate-400">Priority score (weighted)</div>
            </div>
            <div className="text-right text-xs leading-relaxed text-slate-400">
              <div>
                ICP <b className="text-sky-300">{lead.icp_score.toFixed(0)}</b>
              </div>
              <div>
                Completeness <b className="text-sky-300">{lead.completeness_score.toFixed(0)}</b>
              </div>
              <div>
                Confidence <b className="text-emerald-300">{lead.confidence_score.toFixed(0)}</b>
              </div>
            </div>
          </div>

          <Group title="Why this priority">
            {["icp", "completeness", "confidence", "freshness"].map((k) => {
              const w = (sb.priority?.weights?.[k] || 0) * 100;
              const v = sb.priority?.components?.[k] || 0;
              return (
                <div key={k} className="flex items-center justify-between gap-2 py-1">
                  <span className="w-28 text-xs capitalize text-slate-400">{k} · {w.toFixed(0)}%</span>
                  <ScoreBar value={v} color={k === "confidence" ? "bg-emerald-400" : "bg-sky-400"} />
                </div>
              );
            })}
            {icp.notes?.map((n, i) => (
              <div key={i} className={`mt-2 flex items-start gap-1.5 text-[11px] ${n.includes("MARKET GATE") ? "text-amber-300" : "text-slate-500"}`}>
                <span className="mt-0.5 text-teal-400">✦</span>
                <span>{n}</span>
              </div>
            ))}
          </Group>

          <Group title="ICP fit — target profile">
            {Object.entries(icp.breakdown || {}).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between gap-2 py-1">
                <span className="w-28 text-xs capitalize text-slate-400">{k.replace("_", " ")}</span>
                <ScoreBar value={v} color="bg-sky-400" />
              </div>
            ))}
          </Group>

          <Group title="Data quality">
            <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
              <span>Populated fields ({comp.populated?.length || 0}/8)</span>
            </div>
            <div className="mb-2 flex flex-wrap gap-1">
              {(comp.populated || []).map((f) => (
                <span key={f} className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[11px] text-emerald-300">{f.replace("_", " ")}</span>
              ))}
              {(comp.missing || []).map((f) => (
                <span key={f} className="rounded bg-slate-600/20 px-1.5 py-0.5 text-[11px] text-slate-500">{f.replace("_", " ")}</span>
              ))}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge label={`Email ${lead.email_status}`} tone={lead.email_status === "verified" ? "verified" : lead.email_status === "risky" ? "risky" : lead.email_status === "invalid" ? "invalid" : "missing"} />
              <Badge label={`Phone ${lead.phone_status}`} tone={lead.phone_status === "verified" ? "verified" : lead.phone_status === "risky" ? "risky" : "missing"} />
            </div>
            {valid.email?.finding && valid.email.status !== "unknown" && (
              <div className="mt-2 border-t border-edge/60 pt-2 text-[11px] text-slate-400">
                <span className="text-slate-500">Email check:</span> {valid.email.finding}
                {valid.email.issues?.map((i) => (
                  <div key={i} className="mt-0.5 text-amber-300/90">⚠ {i}</div>
                ))}
              </div>
            )}
            {valid.phone?.finding && valid.phone.status === "invalid" && (
              <div className="mt-1 text-[11px] text-amber-300/90">⚠ {valid.phone.finding}</div>
            )}
          </Group>

          <Group title="Profile">
            <Field label="Email">{lead.owner_email || "—"}</Field>
            <Field label="Phone">{lead.owner_phone || lead.company_phone || "—"}</Field>
            <Field label="Employees">{lead.employees ?? "—"}</Field>
            <Field label="Est. revenue">
              {lead.revenue_estimate_usd ? `$${lead.revenue_estimate_usd.toLocaleString()}` : "—"}
            </Field>
            <Field label="LinkedIn">
              {lead.company_linkedin ? (
                <a href={lead.company_linkedin} target="_blank" rel="noreferrer" className="text-teal-300 hover:underline">
                  profile
                </a>
              ) : "—"}
            </Field>
            <Field label="Website">
              {lead.website ? (
                <a href={lead.website} target="_blank" rel="noreferrer" className="text-teal-300 hover:underline">
                  {lead.domain || lead.website}
                </a>
              ) : "—"}
            </Field>
            {lead.description && (
              <p className="mt-2 border-t border-edge/60 pt-2 text-[11px] italic text-slate-400">
                {lead.description}
              </p>
            )}
          </Group>

          <Group title="Sources ({sources.length})">
            {sources.map((s, i) => (
              <div key={i} className="flex items-center justify-between py-1 text-[11px]">
                <span className="text-slate-300">{s.source}</span>
                <span className="text-slate-500">
                  {s.url ? (typeof s.url === "string" ? s.url.replace("fixture:", "fixture/") : s.url) : "manual"}
                </span>
              </div>
            ))}
            <div className="mt-1 flex items-center gap-1.5 text-[11px]">
              <span className={`h-1.5 w-1.5 rounded-full ${lead.freshness_score >= 0.9 ? "bg-emerald-400" : lead.freshness_score >= 0.7 ? "bg-amber-400" : "bg-rose-400"}`} />
              <span className="text-slate-500">
                Freshness {lead.freshness_score.toFixed(2)} · {lead.dedup_group ? "deduplicated" : "single record"}
              </span>
            </div>
          </Group>
        </div>
      </div>
    </div>
  );
}