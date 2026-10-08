import { useState } from "react";
import { api } from "../api";

export function Header({ onScrape, onScraped }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const runScrape = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await api.scrape();
      setMsg(
        `Scraped ${res.parsed} records from 3 public sources → ${res.new_leads} new leads, ${res.deduplicated} duplicates flagged`
      );
      onScraped && onScraped(res);
    } catch (e) {
      setMsg(`Scrape failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <header className="sticky top-0 z-40 border-b border-edge bg-[#1a2133]/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-teal-400 to-sky-500 text-sm font-black text-slate-900">
            S
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-white">SaaSquatch Prioritizer</div>
            <div className="text-[11px] uppercase tracking-wider text-teal-300/80">
              Lead Intelligence
            </div>
          </div>
        </div>
        <nav className="ml-auto flex items-center gap-3 text-xs text-slate-400">
          <button
            onClick={runScrape}
            disabled={busy}
            className="rounded-md bg-gradient-to-r from-teal-500 to-sky-500 px-3 py-2 text-xs font-semibold text-white shadow transition hover:opacity-90 disabled:opacity-50"
          >
            {busy ? "Scraping…" : "Re-scrape fixtures"}
          </button>
        </nav>
      </div>
      {msg && (
        <div className="border-t border-edge/60 bg-teal-500/5 px-6 py-2 text-xs text-teal-200">
          {msg}
        </div>
      )}
    </header>
  );
}