const TIER_STYLES = {
  hot: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30",
  warm: "bg-amber-500/15 text-amber-300 ring-amber-400/30",
  cold: "bg-slate-600/20 text-slate-400 ring-slate-500/30",
};

export function TierPill({ tier }) {
  const label = { hot: "Hot", warm: "Warm", cold: "Cold" }[tier] || tier || "—";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ring-1 ${
        TIER_STYLES[tier] || TIER_STYLES.cold
      }`}
    >
      {label}
    </span>
  );
}

export function ScoreBar({ value, color = "bg-teal-400" }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${color} score-bar`}
          style={{ width: `${v}%` }}
        />
      </div>
      <span className="w-9 text-right text-xs font-semibold tabular-nums text-slate-300">
        {v.toFixed(0)}
      </span>
    </div>
  );
}

export function Badge({ label, tone = "neutral" }) {
  const tones = {
    verified: "bg-emerald-500/15 text-emerald-300 ring-emerald-400/30",
    risky: "bg-amber-500/15 text-amber-300 ring-amber-400/30",
    invalid: "bg-rose-500/15 text-rose-300 ring-rose-400/30",
    missing: "bg-slate-600/20 text-slate-400 ring-slate-500/30",
    unknown: "bg-slate-600/20 text-slate-300 ring-slate-500/40",
    neutral: "bg-white/5 text-slate-300 ring-white/10",
    info: "bg-sky-500/15 text-sky-300 ring-sky-400/30",
  };
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium capitalize ring-1 ${tones[tone] || tones.neutral}`}
    >
      {label}
    </span>
  );
}

export function Field({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="max-w-[60%] truncate text-right text-xs text-slate-200">
        {children}
      </span>
    </div>
  );
}