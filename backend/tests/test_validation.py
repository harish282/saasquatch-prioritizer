"""Field-level validation unit tests (offline: DNS is disabled in conftest)."""

from app.validation import validate_domain, validate_email, validate_phone


class TestValidateEmail:
    def test_rejects_missing(self):
        result = validate_email("")
        assert result["status"] == "unknown"

    def test_rejects_basic_syntax_errors(self):
        for bad in ("jane@", "@acme.com", "jane", "jane@acme", "jane@@acme.com"):
            assert validate_email(bad)["status"] == "invalid", bad

    def test_rejects_invalid_syntax(self):
        assert validate_email("jane doe@example.com")["status"] == "invalid"

    def test_flags_disposable_provider(self):
        result = validate_email("lead@mailinator.com")
        assert result["status"] == "risky"
        assert "disposable" in " ".join(result["issues"]).lower()

    def test_accepts_valid_company_email(self):
        result = validate_email("operations@acme-example.com")
        assert result["status"] == "verified"

    def test_personal_domain_is_a_note_not_a_blocker(self):
        result = validate_email("jane@gmail.com")
        assert result["status"] == "verified"
        assert any("Personal" in i for i in result["issues"])


class TestValidatePhone:
    def test_rejects_missing(self):
        assert validate_phone(None)["status"] == "unknown"

    def test_rejects_non_numeric_garbage(self):
        assert validate_phone("not-a-phone-number")["status"] == "invalid"

    def test_validates_us_paren_format(self):
        # Regression: "(512) 555-0134" used to be flagged invalid because the
        # leading '(' failed the shape regex.
        result = validate_phone("(512) 555-0134", "USA")
        assert result["status"] == "verified"

    def test_validates_international_e164(self):
        result = validate_phone("+44 117 555 0124")
        assert result["status"] == "verified"

    def test_digits_count_fallback(self):
        assert validate_phone("4155550199")["status"] == "verified"

    def test_short_number_is_risky(self):
        result = validate_phone("555-0199")  # 7 digits — plausible, verify first
        assert result["status"] == "risky"

    def test_ridiculously_short_international_number_is_invalid(self):
        result = validate_phone("+999 1 2")  # 4 digits — cannot be a real number
        assert result["status"] == "invalid"


class TestValidateDomain:
    def test_missing_domain(self):
        assert validate_domain(None)["status"] == "unknown"
        assert validate_domain("")["status"] == "unknown"

    def test_malformed_domain(self):
        assert validate_domain("localhost")["status"] == "invalid"
        assert validate_domain("a" * 300 + ".com")["status"] == "invalid"

    def test_offline_host_is_unresolvable_not_a_crash(self):
        # No DNS + getaddrinfo raising (conftest) must degrade, never raise.
        result = validate_domain("acme-example.com")
        assert result["status"] in ("verified", "unresolvable", "unknown")
        assert "ok" in result