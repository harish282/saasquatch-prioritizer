export function Filters({ filters, onChange, stats }) {
  const set = (patch) => onChange({ ...filters, ...patch });

  const select =
    "rounded-lg border border-edge bg-panel px-3 py-2 text-xs text-slate-200 outline-none focus:border-teal-400/60";

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl border border-edge bg-panel/40 p-3">
      <input
        value={filters.q}
        onChange={(e) => set({ q: e.target.value })}
        placeholder="Search company or email…"
        className={`${select} w-56`}
      />
      <select
        value={filters.country}
        onChange={(e) => set({ country: e.target.value })}
        className={select}
      >
        <option value="">All countries</option>
        {(stats?.countries || []).map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>
      <select
        value={filters.industry}
        onChange={(e) => set({ industry: e.target.value })}
        className={`${select} max-w-56`}
      >
        <option value="">All industries</option>
        {(stats?.industries || []).map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <div className="flex items-center gap-1.5">
        {["hot", "warm", "cold"].map((t) => (
          <button
            key={t}
            onClick={() => set({ tier: filters.tier === t ? "" : t })}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold capitalize ring-1 transition ${
              filters.tier === t
                ? t === "hot"
                  ? "bg-emerald-500/20 text-emerald-200 ring-emerald-400/50"
                  : t === "warm"
                    ? "bg-amber-500/20 text-amber-200 ring-amber-400/50"
                    : "bg-slate-600/30 text-slate-200 ring-slate-400/50"
                : "bg-white/5 text-slate-400 ring-white/10 hover:text-slate-200"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <label className="flex items-center gap-2 text-xs text-slate-300">
        <input
          type="checkbox"
          checked={filters.has_email}
          onChange={(e) => set({ has_email: e.target.checked })}
          className="accent-teal-400"
        />
        Have email
      </label>

      <div className="ml-auto flex items-center gap-3">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          Min score
          <input
            type="range"
            min="0"
            max="100"
            value={filters.min_score}
            onChange={(e) => set({ min_score: Number(e.target.value) })}
            className="w-24 accent-teal-400"
          />
          <span className="w-6 text-teal-300 tabular-nums">{filters.min_score}</span>
        </label>
      </div>
    </div>
  );
}