"""Deduplication tests: registry-aware domain normalisation + cluster marking."""

from app.dedup import group_duplicates, normalize_domain
from app.models import Lead


class TestNormalizeDomain:
    def test_plain_domain(self):
        assert normalize_domain("acme.com") == "acme"

    def test_compound_suffix_not_mistaken_for_host(self):
        # Regression: acme.co.uk must NOT become "uk".
        assert normalize_domain("acme.co.uk") == "acme"

    def test_www_and_url_stripping(self):
        assert normalize_domain("https://www.BrightlineElectrical.co.uk") == "brightlineelectrical"

    def test_hyphen_collapsed(self):
        assert normalize_domain("Acme-Corp.biz") == "acmecorp"
        assert normalize_domain("omega-one-LLC.com") == "omegaonellc"

    def test_missing(self):
        assert normalize_domain(None) is None
        assert normalize_domain("") is None


def _lead(company, domain, email, completeness=80.0, confidence=60.0):
    l = Lead(company=company, domain=domain, owner_email=email)
    l.completeness_score = completeness
    l.confidence_score = confidence
    return l


class TestGroupDuplicates:
    def test_same_domain_clusters_as_duplicates(self, fresh_db):
        a = _lead("Acme Cleaning", "acme.com", "a@acme.com", completeness=90.0, confidence=80.0)
        b = _lead("Acme Cleaning Co", "www.acme.com", "b@acme.com", completeness=70.0, confidence=50.0)
        fresh_db.add_all([a, b])
        fresh_db.commit()

        report = group_duplicates(fresh_db)
        assert len(report) == 1
        group = next(iter(report.values()))
        assert group["primary"]["company"] == "Acme Cleaning"
        assert len(group["duplicates"]) == 1

        fresh_db.refresh(a)
        fresh_db.refresh(b)
        assert a.is_primary is True
        assert b.is_primary is False
        assert b.duplicate_of_id == a.id

    def test_compound_suffix_records_are_grouped(self, fresh_db):
        a = _lead("Brightline Electrical", "brightlineelectrical.co.uk", "a@brightlineelectrical.co.uk")
        b = _lead("Brightline Electrical", "brightlineelectrical.com", "b@brightlineelectrical.com")
        fresh_db.add_all([a, b])
        fresh_db.commit()

        report = group_duplicates(fresh_db)
        assert len(report) == 1

    def test_distinct_domains_not_grouped(self, fresh_db):
        a = _lead("Alpha Roofing", "alpharooofing.com", "a@alpha.com")
        b = _lead("Beta Plumbing", "betaplumbing.com", "b@beta.com")
        fresh_db.add_all([a, b])
        fresh_db.commit()

        assert group_duplicates(fresh_db) == {}

    def test_fuzzy_name_match_when_no_domain(self, fresh_db):
        a = _lead("Acme Landscaping", None, "a@acme.com")
        b = _lead("Acme Landscaping Co", None, "b@acme.com")  # "co" is a stopword
        fresh_db.add_all([a, b])
        fresh_db.commit()

        report = group_duplicates(fresh_db)
        assert len(report) == 1