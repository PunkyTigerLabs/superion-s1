import json

import httpx
import pytest
import respx

import superion_s1 as s1
from superion_s1 import AsyncSuperion, Superion, choice, noul, score

BASE = "https://api.punkytigerlabs.com"
REAL = {  # real v6 response to the docs example, 12 Nov 2026
    "model": s1.DEFAULT_MODEL,
    "usage": {"input_tokens": 135, "output_tokens": 0},
    "answers": {
        "refund": {"type": "noul", "noul": 0.9997470683161428},
        "sentiment": {"type": "choice", "probabilities": {"pos": 0.0002855798545093104, "neg": 0.9942880386883389, "neu": 0.005426381457151809}},
        "urgency": {"type": "score", "probabilities": {"0": 1.2e-12, "1": 0.19215297234497805, "2": 0.8078470276538201}},
    },
}
QUESTIONS = {
    "refund": noul("Does the customer ask for a refund or a replacement?"),
    "sentiment": choice("Overall sentiment of the message.", {"pos": "positive", "neg": "negative", "neu": "neutral"}),
    "urgency": score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("SUPERION_API_KEY", "s1k_test")
    monkeypatch.delenv("SUPERION_BASE_URL", raising=False)
    monkeypatch.delenv("SUPERION_MODEL", raising=False)
    monkeypatch.setattr(s1._client.time, "sleep", lambda s: None)


def test_requires_key(monkeypatch):
    monkeypatch.delenv("SUPERION_API_KEY")
    with pytest.raises(s1.SuperionError, match="SUPERION_API_KEY"):
        Superion()


def test_repr_hides_key():
    assert "s1k_test" not in repr(Superion())


def test_builders():
    assert noul("q?") == {"type": "noul", "instructions": "q?", "criteria": {"true": "yes", "false": "no"}}
    assert choice("q", ["a", "b"])["criteria"] == {"a": "a", "b": "b"}
    with pytest.raises(ValueError):
        choice("q", ["only"])
    with pytest.raises(ValueError):
        score("q", [str(i) for i in range(17)])


@respx.mock
def test_decide_sends_exact_wire_format_and_parses():
    route = respx.post(f"{BASE}/v1/systemone").mock(return_value=httpx.Response(200, json=REAL, headers={"X-RateLimit-Limit": "60"}))
    d = Superion().decide("Message: broken laptop", QUESTIONS)
    sent = json.loads(route.calls[0].request.content)
    assert route.calls[0].request.headers["authorization"] == "Bearer s1k_test"
    assert sent == {"model": s1.DEFAULT_MODEL, "state": "Message: broken laptop", "questions": QUESTIONS}
    assert d["refund"].p == pytest.approx(0.99975, abs=1e-4) and d["refund"].yes()
    assert d["sentiment"].best == "neg"
    assert d["urgency"].best == 2 and d["urgency"].best_label == "very urgent"
    assert d["urgency"].expected == pytest.approx(1.8078, abs=1e-3)
    assert 0.9 < d["urgency"].normalized <= 1
    assert d.usage.input_tokens == 135 and d.usage.output_tokens == 0
    assert d.rate_limit == {"x-ratelimit-limit": "60"} and d.balance_usd is None
    assert list(d) == ["refund", "sentiment", "urgency"]


@respx.mock
def test_helpers_single_question():
    respx.post(f"{BASE}/v1/systemone").mock(side_effect=[
        httpx.Response(200, json={"model": "m", "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"q": {"type": "noul", "noul": 0.2}}}),
        httpx.Response(200, json={"model": "m", "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"q": {"type": "choice", "probabilities": {"a": 0.3, "b": 0.7}}}}),
        httpx.Response(200, json={"model": "m", "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"q": {"type": "score", "probabilities": {"0": 0.5, "1": 0.5}}}}),
    ])
    c = Superion(model="custom")
    assert c.noul("s", "q?") == 0.2
    assert c.choice("s", "q", ["a", "b"]).best == "b"
    assert c.score("s", "q", ["lo", "hi"]).expected == 0.5


@respx.mock
def test_retries_429_with_retry_after_then_succeeds():
    route = respx.post(f"{BASE}/v1/systemone").mock(side_effect=[
        httpx.Response(429, json={"error": "server busy: queue full, retry shortly"}, headers={"Retry-After": "5"}),
        httpx.Response(503, json={"error": "service temporarily unavailable"}, headers={"Retry-After": "15"}),
        httpx.Response(200, json=REAL),
    ])
    assert Superion().decide("s", QUESTIONS)["refund"].p > 0.9
    assert route.call_count == 3


@respx.mock
def test_daily_quota_is_not_slept_through():
    route = respx.post(f"{BASE}/v1/systemone").mock(return_value=httpx.Response(
        429, json={"error": "daily token limit reached"}, headers={"Retry-After": "43200"}))
    with pytest.raises(s1.RateLimitError) as e:
        Superion().decide("s", QUESTIONS)
    assert e.value.retry_after == 43200 and route.call_count == 1


@respx.mock
@pytest.mark.parametrize("status,body,cls", [
    (400, {"error": "unknown model"}, s1.BadRequestError),
    (401, {"error": "invalid API key"}, s1.AuthenticationError),
    (402, {"error": "insufficient balance", "balance_usd": -0.000004}, s1.InsufficientBalanceError),
    (413, {"error": "request too large"}, s1.RequestTooLargeError),
    (422, {"error": "question s: score supports 2..16 levels"}, s1.UnprocessableError),
])
def test_errors_are_typed_and_not_retried(status, body, cls):
    route = respx.post(f"{BASE}/v1/systemone").mock(return_value=httpx.Response(status, json=body))
    with pytest.raises(cls) as e:
        Superion().decide("s", QUESTIONS)
    assert e.value.status_code == status and e.value.message == body["error"]
    assert route.call_count == 1
    if status == 402:
        assert e.value.balance_usd == -0.000004


@respx.mock
def test_connection_error_retried_then_raised():
    route = respx.post(f"{BASE}/v1/systemone").mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(s1.APIConnectionError):
        Superion(max_retries=1).decide("s", QUESTIONS)
    assert route.call_count == 2


def test_client_side_validation_saves_a_call():
    with pytest.raises(ValueError, match="noul criteria"):
        Superion().decide("s", {"q": {"type": "noul", "instructions": "?", "criteria": {"true": "y"}}})
    with pytest.raises(ValueError):
        Superion().decide("", QUESTIONS)


@respx.mock
def test_models_usage_health():
    m = respx.get(f"{BASE}/v1/models").mock(return_value=httpx.Response(200, json={"data": [{"id": s1.DEFAULT_MODEL}]}))
    respx.get(f"{BASE}/v1/usage").mock(return_value=httpx.Response(200, json={"key_id": "k", "plan": "free"}))
    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    c = Superion()
    assert c.models()[0]["id"] == s1.DEFAULT_MODEL
    assert "authorization" not in m.calls[0].request.headers  # public endpoint: key not sent
    assert c.usage()["plan"] == "free"
    assert c.health()


@respx.mock
async def test_async_client(monkeypatch):
    async def nosleep(_):
        return None
    monkeypatch.setattr(s1._client.asyncio, "sleep", nosleep)
    respx.post(f"{BASE}/v1/systemone").mock(side_effect=[
        httpx.Response(503, json={"error": "service temporarily unavailable"}, headers={"Retry-After": "1"}),
        httpx.Response(200, json=REAL)])
    async with AsyncSuperion() as c:
        d = await c.decide("s", QUESTIONS)
    assert d["sentiment"].best == "neg"
