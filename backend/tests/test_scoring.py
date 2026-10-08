"""Scoring engine tests: ICP market gate, outreachability gate, tiers."""

from app.models import Lead
from app.scoring import score_lead


def make_lead(**overrides) -> Lead:
    defaults = dict(
        company="Acme Test Cleaning",
        industry="house cleaning service",
        country="USA",
        city="Austin",
        employees=25,
        revenue_estimate_usd=500_000,
        website="https://acme-example.com",
        domain="acme-example.com",
        owner_first_name="Jane",
        owner_last_name="Roe",
        owner_email="jane@acme-example.com",
        owner_phone="(512) 555-0134",
        sources=[{"source": "fixture:business_directory", "url": "fixture:card"}],
    )
    defaults.update(overrides)
    return Lead(**defaults)


class TestMarketGate:
    def test_out_of_market_record_can_never_rank_hot(self):
        # Perfect data, wrong market: German engineering corp, 12k staff, $50M.
        lead = make_lead(
            country="Germany",
            industry="Precision Engineering GmbH",
            employees=12_000,
            revenue_estimate_usd=50_000_000,
            sources=[{"source": "public_registry"}],
        )
        score_lead(lead)
        assert lead.icp_score < 60
        assert lead.priority_score == 54.9
        assert lead.tier == "cold"
        notes = lead.score_breakdown["icp"]["notes"]
        assert any("MARKET GATE" in n for n in notes)

    def test_corporate_size_drag(self):
        lead = make_lead(employees=8_000)
        score_lead(lead)
        assert lead.score_breakdown["icp"]["breakdown"]["size"] == 15.0

    def test_off_market_country_penalised(self):
        lead = make_lead(country="Germany")
        score_lead(lead)
        assert lead.score_breakdown["icp"]["breakdown"]["country"] == 45.0


class TestOutreachabilityGate:
    def test_no_contacts_caps_confidence_and_stays_sub_hot(self):
        # Rich lead on every dimension EXCEPT contact channels. With 3+ sources
        # raw confidence is ~26 (domain + corroboration) -> capped at 22.
        lead = make_lead(
            owner_email=None, owner_phone=None, company_phone=None,
            sources=[
                {"source": "a", "url": ""},
                {"source": "b", "url": ""},
                {"source": "c", "url": ""},
            ],
        )
        score_lead(lead)
        assert lead.confidence_score == 22.0
        assert lead.priority_score < 80
        assert lead.tier == "warm"
        assert lead.email_status == "missing"

    def test_single_channel_still_reachable(self):
        lead = make_lead(owner_phone=None, company_phone=None)
        score_lead(lead)
        assert lead.confidence_score > 22.0  # email present -> not capped


class TestTiers:
    def test_ideal_lead_is_hot(self):
        lead = make_lead(sources=[
            {"source": "a", "url": ""},
            {"source": "b", "url": ""},
            {"source": "c", "url": ""},
        ])
        score_lead(lead)
        assert lead.tier == "hot"
        assert lead.priority_score >= 80

    def test_sparse_lead_is_cold_or_warm_never_hot(self):
        lead = make_lead(
            owner_email=None, owner_phone=None, company_phone=None,
            city=None, employees=None, revenue_estimate_usd=None, owner_first_name=None,
            owner_last_name=None, company="Little known co",
        )
        score_lead(lead)
        assert lead.tier in ("cold", "warm")
        assert lead.priority_score < 80

    def test_completeness_counts_high_value_fields(self):
        lead = make_lead(owner_phone=None, company_phone=None)
        score_lead(lead)
        comp = lead.score_breakdown["completeness"]
        assert "owner_email" in comp["populated"]
        assert "phone" in comp["missing"]


class TestBreakdown:
    def test_weights_sum_to_one(self):
        lead = make_lead()
        score_lead(lead)
        weights = lead.score_breakdown["priority"]["weights"]
        assert sum(weights.values()) == 1.0
        assert set(weights) == {"icp", "completeness", "confidence", "freshness"}

    def test_priority_is_a_weighted_average(self):
        lead = make_lead()
        score_lead(lead)
        sb = lead.score_breakdown["priority"]
        expected = sum(
            v * lead.score_breakdown["priority"]["weights"][k]
            for k, v in sb["components"].items()
        )
        assert abs(lead.priority_score - round(expected, 1)) < 0.15

    def test_freshness_bonus(self):
        lead = make_lead()
        score_lead(lead)
        assert lead.freshness_score == 1.0  # captured just now