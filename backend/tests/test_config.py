from app.core.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, FEATHERLESS_API_KEY="x", **overrides)


def _secret_errors(s: Settings) -> list[str]:
    return [e for e in s.validate() if "SECRET_KEY" in e]


def test_default_secret_key_is_rejected():
    assert _secret_errors(_settings(SECRET_KEY="change-me-in-production"))


def test_short_secret_key_is_rejected():
    assert _secret_errors(_settings(SECRET_KEY="too-short"))


def test_long_random_secret_key_is_accepted():
    assert not _secret_errors(_settings(SECRET_KEY="k" * 40))


def test_dedicated_jwt_secret_satisfies_validation():
    assert not _secret_errors(_settings(SECRET_KEY="change-me-in-production", JWT_SECRET="j" * 40))


def test_admin_emails_are_parsed_case_insensitively():
    s = _settings(SECRET_KEY="k" * 40, ADMIN_EMAILS=" Admin@Example.com, ops@example.com ,")
    assert s.admin_emails == {"admin@example.com", "ops@example.com"}
