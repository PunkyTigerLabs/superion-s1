import json
import os

import httpx
import pytest
import respx
from llama_index.core.tools.tool_spec.base import BaseToolSpec

from llama_index.tools.superion import SuperionToolSpec

URL = "https://api.punkytigerlabs.com/v1/systemone"


def ok(answer):
    return httpx.Response(200, json={"model": "m", "usage": {"input_tokens": 9, "output_tokens": 0}, "answers": {"q": answer}})


def test_class():
    assert BaseToolSpec.__name__ in [b.__name__ for b in SuperionToolSpec.__mro__]


def test_requires_key(monkeypatch):
    monkeypatch.delenv("SUPERION_API_KEY", raising=False)
    with pytest.raises(ValueError, match="SUPERION_API_KEY"):
        SuperionToolSpec()


def test_tool_list_has_metadata():
    tools = SuperionToolSpec(api_key="s1k_fake").to_tool_list()
    assert [t.metadata.name for t in tools] == ["decide_yes_no", "classify", "score"]
    schema = tools[1].metadata.fn_schema.model_json_schema()
    assert set(schema["required"]) == {"text", "question", "options"}


@respx.mock
def test_calls():
    respx.post(URL).mock(side_effect=[
        ok({"type": "noul", "noul": 0.91}),
        ok({"type": "choice", "probabilities": {"billing": 0.7, "tech": 0.3}}),
        ok({"type": "score", "probabilities": {"0": 0.0, "1": 1.0}}),
    ])
    spec = SuperionToolSpec(api_key="s1k_fake")
    assert json.loads(spec.decide_yes_no("t", "q?")) == {"p_yes": 0.91}
    assert json.loads(spec.classify("t", "q", ["billing", "tech"]))["best"] == "billing"
    assert json.loads(spec.score("t", "q", ["low", "high"]))["best"] == "high"


@respx.mock
async def test_async_tool():
    respx.post(URL).mock(return_value=ok({"type": "noul", "noul": 0.2}))
    tool = SuperionToolSpec(api_key="s1k_fake").to_tool_list()[0]
    out = await tool.acall(text="t", question="q?")
    assert json.loads(out.content) == {"p_yes": 0.2}


@pytest.mark.skipif(not (os.environ.get("S1_LIVE") and os.environ.get("SUPERION_API_KEY")), reason="live")
def test_live():
    spec = SuperionToolSpec()
    assert json.loads(spec.classify("Ticket: my card was charged twice", "Which team should handle it?",
                                    ["billing", "tech", "sales"]))["best"] == "billing"
