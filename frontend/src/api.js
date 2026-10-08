const BASE = "/api";

async function get(path, params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  const url = BASE + path + (qs.toString() ? `?${qs}` : "");
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  stats: () => get("/stats"),
  leads: (params) => get("/leads", { per_page: 100, ...params }),
  lead: (id) => get(`/leads/${id}`),
  dedup: () => get("/report/dedup"),
  scrape: () => post("/scrape", { mode: "fixture" }),
  resolve: (id) => post(`/leads/${id}/resolve`),
  exportUrl: (params) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, v);
    });
    return `${BASE}/export.csv?${qs}`;
  },
};