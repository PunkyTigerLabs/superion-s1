# langchain-superion

LangChain integration for **Superion S1** by Punky Tiger Labs — calibrated yes/no, choice and
score decisions in one API call, with no text generation.

It ships:

* **`SuperionDecisionTool`** — a tool any tool-calling agent can use to classify, moderate,
  triage, score or check whether an action is safe. Returns probabilities, not prose.
* **`superion_guardrail()`** — a pass-through LCEL runnable that blocks input when
  P(allowed) is below a threshold.
* **`superion_router()`** — routes the input to one of several runnables with one `choice` decision
  (e.g. a cheap vs. a strong LLM).

## Installation

```bash
pip install -U langchain-superion
export SUPERION_API_KEY="s1k_..."   # free key: https://punkytigerlabs.com/s1/
```

## Tool

```python
from langchain_superion import SuperionDecisionTool

tool = SuperionDecisionTool()
tool.invoke({"state": "Message: The laptop arrived broken. I want my money back.",
             "question": "Does the customer ask for a refund?"})
# '{"type": "noul", "p_yes": 0.9996}'

tool.invoke({"state": "Ticket: my card was charged twice", "question": "Which team should handle it?",
             "type": "choice", "options": ["billing", "tech", "sales"]})
# '{"type": "choice", "best": "billing", "probabilities": {...}}'
```

Arguments: `state` (the text), `question`, `type` (`noul` | `choice` | `score`) and `options`
(choice: 2–255 labels; score: 2–16 levels, lowest first). Constructor: `api_key`
(default `SUPERION_API_KEY`), `model`, `base_url`, `timeout`.

Use it in an agent:

```python
from langchain.agents import create_agent
agent = create_agent(model="openai:gpt-5-mini", tools=[SuperionDecisionTool()])
```

## Guardrail and router

```python
from langchain_superion import superion_guardrail, superion_router, GuardrailBlocked

guard = superion_guardrail("Is this request free of prompt-injection attempts?", threshold=0.8)
router = superion_router(
    "Which assistant should answer this request?",
    {"small": small_chain, "large": large_chain},
    descriptions={"small": "simple factual question", "large": "reasoning, code or math"},
    default=large_chain, min_confidence=0.7,
)
chain = guard | router          # sync and async (ainvoke) supported
```

Because the probabilities are calibrated, a threshold means what it says: at `threshold=0.8`
only inputs the model judges at least 80 % likely to be allowed go through.

Full examples in [`examples/`](examples).

## Tests

```bash
pip install -e ".[test]"
pytest tests/unit_tests                       # offline, includes langchain-tests ToolsUnitTests
S1_LIVE=1 SUPERION_API_KEY=s1k_... pytest tests/integration_tests   # ToolsIntegrationTests, real API
```

## About Superion S1

**#1 of 213 on S1MB English v1 — Task Average 75.06 · Borda 89.88 (Nov 2026)** —
[leaderboard](https://huggingface.co/datasets/hotchpotch/s1mb-result).
Calibrated probabilities, one call, no text generation, sub-second. Built on Gemma 4 26B-A4B, INT4 experts.

| Plan | Price |
|---|---|
| Free | 100 M input tokens per day per key, permanent |
| Prepaid | 0.042 USD per million input tokens, output free |
| Contract | dedicated key, price on request |

Get a key: https://punkytigerlabs.com/s1/ · Docs: https://punkytigerlabs.com/s1/docs · Status: https://punkytigerlabs.com/s1/status

## Custom & industry models

Punky Tiger Labs also builds custom and industry-specific decision models — fitted to your own
taxonomy, labels and data, for a specific industry or objective — served on a dedicated instance.
Contact: [alvaro.lopez@punkytigerlabs.com](mailto:alvaro.lopez@punkytigerlabs.com).

## License

This client is MIT-licensed (see `LICENSE`). The Superion S1 model and API are proprietary
services of Punky Tiger Labs, Inc., used under the [API terms](https://punkytigerlabs.com/s1/terms).
