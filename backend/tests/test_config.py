from app.core.config import Settings


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, GEMINI_API_KEY="x", **overrides)


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


def _llm(**overrides) -> Settings:
    # Blank every provider key first: the real environment (e.g. CI) may define some of them.
    keys = {"GEMINI_API_KEY": "", "DEEPSEEK_API_KEY": ""}
    return Settings(_env_file=None, SECRET_KEY="k" * 40, **{**keys, **overrides})


def test_gemini_is_used_when_its_key_is_set():
    s = _llm(GEMINI_API_KEY="g", DEEPSEEK_API_KEY="d")
    assert s.llm_provider == "gemini"
    assert s.effective_llm_api_key == "g"
    assert s.effective_llm_model == "gemini-3.5-flash"
    assert s.effective_llm_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"


def test_gemini_model_is_configurable_and_ignores_other_providers_models():
    s = _llm(GEMINI_API_KEY="g", GEMINI_MODEL="gemini-2.5-pro", LLM_MODEL="deepseek-chat")
    assert s.effective_llm_model == "gemini-2.5-pro"


def test_deepseek_still_works_without_gemini():
    s = _llm(DEEPSEEK_API_KEY="d")
    assert s.llm_provider == "deepseek"
    assert s.effective_llm_model == "deepseek-chat"
    assert s.effective_llm_base_url == "https://api.deepseek.com/v1"


def test_no_key_means_no_provider():
    assert _llm().llm_provider == "none"


def test_migration_url_adds_the_async_driver_to_a_plain_postgres_url(monkeypatch):
    from app.core import database

    monkeypatch.setattr(database.settings, "DATABASE_URL", "postgresql://u:p@db.internal:5432/app")
    assert database.get_migration_database_url() == "postgresql+asyncpg://u:p@db.internal:5432/app"

    monkeypatch.setattr(database.settings, "DATABASE_URL", "postgresql+asyncpg://u:p@db.internal:5432/app")
    assert database.get_migration_database_url() == "postgresql+asyncpg://u:p@db.internal:5432/app"
