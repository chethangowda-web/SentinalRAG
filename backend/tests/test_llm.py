from unittest.mock import MagicMock, patch

import pytest

from app.services import llm

GEMINI_429 = (
    "Error code: 429 - [{'error': {'code': 429, 'message': 'You exceeded your current quota. "
    "* Quota exceeded for metric: generate_content_free_tier_requests, limit: 5, "
    "model: gemini-2.5-flash Please retry in 32.375178095s.'}}]"
)


def test_rate_limit_is_recognised_from_status_or_message():
    exc = Exception("boom")
    exc.status_code = 429
    assert llm.is_rate_limit_error(exc)
    assert llm.is_rate_limit_error(Exception(GEMINI_429))
    assert not llm.is_rate_limit_error(Exception("Error code: 500 - server error"))


def test_wait_follows_the_providers_hint_plus_a_second():
    assert llm.rate_limit_wait_seconds(Exception(GEMINI_429), attempt=0) == pytest.approx(33.375, abs=0.01)


def test_wait_is_capped_and_has_a_default_without_a_hint():
    assert llm.rate_limit_wait_seconds(Exception("429 retry in 900s"), 0) == llm.MAX_RATE_LIMIT_WAIT_SECONDS
    assert llm.rate_limit_wait_seconds(Exception("429 too many requests"), 0) == 10.0
    assert llm.rate_limit_wait_seconds(Exception("429 too many requests"), 1) == 20.0


def test_overloaded_503_is_retried_after_seconds_not_tens_of_seconds():
    overloaded = Exception("Error code: 503 - This model is currently experiencing high demand.")
    assert llm.rate_limit_wait_seconds(overloaded, 0) == 2.0
    assert llm.rate_limit_wait_seconds(overloaded, 1) == 4.0


def test_invoke_waits_out_one_rate_limit_then_succeeds():
    model = MagicMock()
    model.invoke.side_effect = [Exception(GEMINI_429), "answer"]
    with patch("app.services.llm.time.sleep") as sleep:
        assert llm.invoke_with_retry(model, "q") == "answer"
    sleep.assert_called_once()
    assert model.invoke.call_count == 2


def test_invoke_gives_up_after_the_allowed_retries():
    model = MagicMock()
    model.invoke.side_effect = Exception(GEMINI_429)
    with patch("app.services.llm.time.sleep"), pytest.raises(Exception, match="429"):
        llm.invoke_with_retry(model, "q", rate_limit_retries=1)
    assert model.invoke.call_count == 2


def test_other_errors_are_not_retried():
    model = MagicMock()
    model.invoke.side_effect = Exception("Error code: 500 - boom")
    with patch("app.services.llm.time.sleep") as sleep, pytest.raises(Exception, match="500"):
        llm.invoke_with_retry(model, "q")
    sleep.assert_not_called()
    assert model.invoke.call_count == 1


def test_build_llm_returns_none_without_a_key():
    with patch.object(llm.settings, "GEMINI_API_KEY", ""), patch.object(llm.settings, "DEEPSEEK_API_KEY", ""):
        assert llm.build_llm(max_tokens=10, timeout=5) is None


GEMINI_503 = "Error code: 503 - [{'error': {'code': 503, 'message': 'This model is currently experiencing high demand.'}}]"


def test_transient_provider_errors_are_recognised():
    assert llm.is_transient_error(Exception(GEMINI_503))
    exc = Exception("boom")
    exc.status_code = 502
    assert llm.is_transient_error(exc)
    assert not llm.is_transient_error(Exception("Error code: 401 - invalid key"))
    assert not llm.is_transient_error(Exception("Error code: 400 - bad request"))


def test_invoke_retries_a_503_and_then_succeeds():
    model = MagicMock()
    model.invoke.side_effect = [Exception(GEMINI_503), "answer"]
    with patch("app.services.llm.time.sleep") as sleep:
        assert llm.invoke_with_retry(model, "q") == "answer"
    sleep.assert_called_once()


def test_auth_errors_are_never_retried():
    model = MagicMock()
    model.invoke.side_effect = Exception("Error code: 401 - invalid key")
    with patch("app.services.llm.time.sleep") as sleep, pytest.raises(Exception, match="401"):
        llm.invoke_with_retry(model, "q")
    sleep.assert_not_called()
