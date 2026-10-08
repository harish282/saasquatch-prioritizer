const CARD =
  "rounded-xl border border-edge bg-panel/60 p-4 flex flex-col gap-1";

function Stat({ label, value, sub, accent }) {
  return (
    <div className={CARD}>
      <span
        className={`text-2xl font-semibold tabular-nums ${
          accent ? `text-${accent}-300` : "text-white"
        }`}
      >
        {value}
      </span>
      <span className="text-xs text-slate-400">{label}</span>
      {sub && <span className="text-[11px] text-slate-500">{sub}</span>}
    </div>
  );
}

export function StatsBar({ stats }) {
  if (!stats)
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={`${CARD} h-20 animate-pulse`} />
        ))}
      </div>
    );

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
      <div className={CARD} style={{ gridColumn: "span 2" }}>
        <div className="flex items-center gap-3">
          <span className="text-3xl font-semibold text-white tabular-nums">
            {stats.total}
          </span>
          <div className="flex gap-1.5">
            <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-[11px] font-semibold text-emerald-300">
              {stats.hot} hot
            </span>
            <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber-300">
              {stats.warm} warm
            </span>
            <span className="rounded bg-slate-600/20 px-1.5 py-0.5 text-[11px] font-semibold text-slate-400">
              {stats.cold} cold
            </span>
          </div>
        </div>
        <span className="text-xs text-slate-400">
          Leads · {stats.duplicates} duplicates flagged
        </span>
      </div>
      <Stat label="Avg confidence" value={`${stats.avg_confidence}%`} sub="validated contacts" accent="emerald" />
      <Stat label="Avg completeness" value={`${stats.avg_completeness}%`} sub="of 8 key fields" accent="sky" />
      <Stat label="Leads w/ email" value={`${stats.with_email}/${stats.total}`} sub={`${stats.verified_emails} verified`} />
      <div className="rounded-xl border border-edge bg-panel/60 p-4 flex flex-col justify-center gap-1">
        <span className="text-[11px] uppercase tracking-wider text-slate-500">
          Outreach-ready
        </span>
        <span className="text-xs text-slate-300">
          <b className="text-emerald-300 tabular-nums">{stats.verified_emails}</b> verified
          emails ready to export
        </span>
        <span className="text-[11px] text-slate-500">
          {stats.hot + stats.warm} contactable now
        </span>
      </div>
    </div>
  );
}