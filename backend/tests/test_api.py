"""API smoke tests against a freshly seeded database (37 leads)."""


class TestHealthAndStats:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["leads"] == 37

    def test_stats_aggregates(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        s = r.json()
        assert s["total"] == 37
        assert s["hot"] + s["warm"] + s["cold"] == 37
        assert s["duplicates"] == 17
        assert s["cold"] >= 1
        assert None not in s["countries"]
        assert None not in s["industries"]


class TestLeadQueue:
    def test_sorted_by_priority_desc(self, client):
        r = client.get("/api/leads", params={"per_page": 50})
        leads = r.json()["leads"]
        scores = [l["priority_score"] for l in leads]
        assert scores == sorted(scores, reverse=True)

    def test_default_excludes_missing_columns_from_sort_failure(self, client):
        r = client.get("/api/leads", params={"sort": "company", "order": "asc"})
        assert r.status_code == 200

    def test_tier_filter(self, client):
        r = client.get("/api/leads", params={"tier": "hot"})
        body = r.json()
        assert body["total"] > 0
        assert all(l["tier"] == "hot" for l in body["leads"])

    def test_search_filter(self, client):
        r = client.get("/api/leads", params={"q": "berry"})
        leads = r.json()["leads"]
        assert leads  # Berry Clean appears multiple times
        assert all("berry" in (l["company"] or "").lower() or (l["owner_email"] or "").lower().startswith("berry")
                   for l in leads)

    def test_market_gate_lead_is_visible_and_cold(self, client):
        r = client.get("/api/leads", params={"q": "heinemann"})
        body = r.json()
        assert body["total"] == 1
        assert body["leads"][0]["tier"] == "cold"
        assert body["leads"][0]["priority_score"] == 54.9


class TestDedupReport:
    def test_reports_fourteen_clusters(self, client):
        r = client.get("/api/report/dedup")
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 14
        for group in body["groups"]:
            assert group["primary"]
            assert group["duplicates"]

    def test_resolve_keeps_primary_and_removes_dupes(self, client):
        report = client.get("/api/report/dedup").json()
        group = report["groups"][0]
        primary, dups = group["primary"], group["duplicates"]
        assert dups

        r = client.post(f"/api/leads/{primary['id']}/resolve")
        assert r.status_code == 200
        assert r.json()["removed_duplicates"] == len(dups)

        after = client.get("/api/report/dedup").json()
        assert after["count"] == report["count"] - 1
        assert primary["id"] not in {g["primary"]["id"] for g in after["groups"]}

    def test_resolve_requires_dedup_group(self, client):
        r = client.post("/api/leads/nonexistent/resolve")
        assert r.status_code == 404


class TestExport:
    def test_csv_header_and_columns(self, client):
        r = client.get("/api/export.csv")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        text = r.text
        rows = text.splitlines()
        assert len(rows) == 38  # header + 37 leads
        assert "company" in rows[0]
        assert "priority_score" in rows[0]
        assert "tier" in rows[0]

    def test_csv_respects_filters(self, client):
        r = client.get("/api/export.csv", params={"tier": "hot"})
        rows = r.text.splitlines()
        assert len(rows) > 1
        header = rows[0].split(",")
        tier_idx = header.index("tier")
        assert all(row.split(",")[tier_idx] == "hot" for row in rows[1:])


class TestScrape:
    def test_fixture_mode_reparses_all_sources(self, client):
        r = client.post("/api/scrape", json={"mode": "fixture", "source": "business_directory"})
        assert r.status_code == 200
        body = r.json()
        assert body["parsed"] == 15  # card + table HTML + JSON registry

    def test_url_mode_is_disabled(self, client):
        r = client.post("/api/scrape", json={"mode": "url", "html": "<p>x</p>"})
        assert r.status_code == 422

    def test_get_single_lead(self, client):
        leads = client.get("/api/leads", params={"per_page": 1}).json()["leads"]
        r = client.get(f"/api/leads/{leads[0]['id']}")
        assert r.status_code == 200
        assert r.json()["lead"]["id"] == leads[0]["id"]
        assert r.json()["lead"]["score_breakdown"]