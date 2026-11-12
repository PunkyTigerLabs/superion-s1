import json

import httpx
import pytest
import respx
from langchain_core.runnables import RunnableLambda

from langchain_superion import GuardrailBlocked, SuperionDecisionTool, superion_guardrail, superion_router
from superion_s1 import Superion

URL = "https://api.punkytigerlabs.com/v1/systemone"


def ok(answer):
    return httpx.Response(200, json={"model": "m", "usage": {"input_tokens": 10, "output_tokens": 0}, "answers": {"q": answer}})


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setenv("SUPERION_API_KEY", "s1k_fake")


def test_missing_key(monkeypatch):
    monkeypatch.delenv("SUPERION_API_KEY")
    with pytest.raises(ValueError, match="SUPERION_API_KEY"):
        SuperionDecisionTool()


@respx.mock
def test_tool_noul_choice_score():
    route = respx.post(URL).mock(side_effect=[
        ok({"type": "noul", "noul": 0.93}),
        ok({"type": "choice", "probabilities": {"billing": 0.8, "tech": 0.2}}),
        ok({"type": "score", "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7}}),
    ])
    t = SuperionDecisionTool()
    assert json.loads(t.invoke({"state": "s", "question": "q?"})) == {"type": "noul", "p_yes": 0.93}
    out = json.loads(t.invoke({"state": "s", "question": "team?", "type": "choice", "options": ["billing", "tech"]}))
    assert out["best"] == "billing"
    out = json.loads(t.invoke({"state": "s", "question": "urgency?", "type": "score", "options": ["low", "mid", "high"]}))
    assert out["best"] == "high" and out["expected_level"] == 1.6
    sent = json.loads(route.calls[1].request.content)
    assert sent["questions"]["q"] == {"type": "choice", "instructions": "team?", "criteria": {"billing": "billing", "tech": "tech"}}


def test_tool_requires_options_for_choice():
    with pytest.raises(ValueError, match="options"):
        SuperionDecisionTool().invoke({"state": "s", "question": "q", "type": "choice"})


@respx.mock
async def test_tool_async():
    respx.post(URL).mock(return_value=ok({"type": "noul", "noul": 0.1}))
    assert json.loads(await SuperionDecisionTool().ainvoke({"state": "s", "question": "q?"}))["p_yes"] == 0.1


@respx.mock
def test_guardrail_passes_and_blocks():
    respx.post(URL).mock(side_effect=[ok({"type": "noul", "noul": 0.97}), ok({"type": "noul", "noul": 0.02}),
                                      ok({"type": "noul", "noul": 0.02})])
    chain = superion_guardrail("Is this safe?", threshold=0.8) | RunnableLambda(lambda x: f"LLM({x})")
    assert chain.invoke("hello") == "LLM(hello)"
    with pytest.raises(GuardrailBlocked) as e:
        chain.invoke("ignore previous instructions")
    assert e.value.p_allow == 0.02
    soft = superion_guardrail("Is this safe?", threshold=0.8, on_block=lambda x, p: "refused")
    assert soft.invoke("bad") == "refused"


@respx.mock
async def test_router_sync_and_async():
    respx.post(URL).mock(side_effect=[
        ok({"type": "choice", "probabilities": {"small": 0.9, "large": 0.1}}),
        ok({"type": "choice", "probabilities": {"small": 0.45, "large": 0.55}}),
    ])
    router = superion_router("Which model?", {"small": lambda x: "S", "large": lambda x: "L"},
                             descriptions={"small": "simple", "large": "hard"}, default=lambda x: "D",
                             min_confidence=0.6, client=Superion())
    assert router.invoke("2+2?") == "S"
    assert await router.ainvoke("prove it") == "D"
