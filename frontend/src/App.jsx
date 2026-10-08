import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { Header } from "./components/Header";
import { StatsBar } from "./components/StatsBar";
import { Filters } from "./components/Filters";
import { LeadTable } from "./components/LeadTable";
import { ScoreDrawer } from "./components/ScoreDrawer";
import { DedupPanel } from "./components/DedupPanel";

const DEFAULT_FILTERS = {
  q: "",
  country: "",
  industry: "",
  tier: "",
  min_score: 0,
  has_email: false,
};

export default function App() {
  const [stats, setStats] = useState(null);
  const [leads, setLeads] = useState([]);
  const [total, setTotal] = useState(0);
  const [report, setReport] = useState(null);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState({ field: "priority_score", order: "desc" });
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("queue");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        ...filters,
        min_score: filters.min_score || undefined,
        sort: sort.field,
        order: sort.order,
        include_duplicates: true,
      };
      const [statsRes, leadsRes, dedupRes] = await Promise.all([
        api.stats(),
        api.leads(params),
        api.dedup(),
      ]);
      setStats(statsRes);
      setLeads(leadsRes.leads);
      setTotal(leadsRes.total);
      setReport(dedupRes);
      setError(null);
    } catch (e) {
      console.error(e);
      setError(`Failed to load data: ${e.message}. Is the backend running on :8000?`);
    } finally {
      setLoading(false);
    }
  }, [filters, sort]);

  useEffect(() => {
    load();
  }, [load]);

  const openFirstLead = async (id) => {
    const res = await api.lead(id);
    setSelected(res.lead);
  };

  const handleSort = (field) => {
    setSort((s) =>
      s.field === field ? { field, order: s.order === "desc" ? "asc" : "desc" } : { field, order: "desc" }
    );
  };

  const refresh = async (extraMsg) => {
    await load();
    if (extraMsg) console.log(extraMsg);
  };

  return (
    <div className="min-h-screen bg-ink text-slate-200">
      <Header
        onScraped={() => {
          setActiveTab("dedup");
          refresh();
        }}
      />

      <main className="mx-auto max-w-7xl space-y-4 px-6 py-6">
        {error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        <StatsBar stats={stats} />

        <div className="flex gap-3 border-b border-edge pb-0">
          {[
            { id: "queue", label: `Lead Queue · ${total}` },
            { id: "dedup", label: `Deduplication · ${report?.count ?? "…"}` },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`rounded-t-lg px-4 py-2.5 text-sm font-medium transition ${
                activeTab === t.id
                  ? "border-b-2 border-teal-400 text-white"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {activeTab === "queue" ? (
          <>
            <Filters filters={filters} onChange={setFilters} stats={stats} />
            {loading ? (
              <div className="flex h-40 items-center justify-center text-sm text-slate-500">
                Loading…
              </div>
            ) : (
              <LeadTable
                leads={leads}
                sort={sort}
                onSort={handleSort}
                onOpen={openFirstLead}
                filters={filters}
                onResolve={refresh}
              />
            )}
          </>
        ) : (
          <DedupPanel report={report} onResolve={refresh} />
        )}
      </main>

      <ScoreDrawer lead={selected} onClose={() => setSelected(null)} />

      <footer className="mx-auto max-w-7xl px-6 py-6 text-center text-[11px] text-slate-600">
        SaaSquatch Prioritizer — 5-hour build · scoring &amp; data-quality layer for lead-gen · FastAPI + React
      </footer>
    </div>
  );
}