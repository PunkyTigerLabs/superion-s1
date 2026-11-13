# Superion S1 Tool (LlamaIndex)

```bash
pip install llama-index-tools-superion
export SUPERION_API_KEY="s1k_..."   # free key: https://punkytigerlabs.com/s1/
```

This tool spec gives LlamaIndex agents calibrated judgement from **Superion S1** by Punky Tiger
Labs: yes/no, choice and score decisions about a text, with calibrated probabilities from one
API call and no text generation. Use it to classify, moderate, triage, rate leads or decide
whether an action is safe.

| tool | arguments | returns (JSON) |
|---|---|---|
| `decide_yes_no` | `text`, `question` | `{"p_yes": 0.97}` |
| `classify` | `text`, `question`, `options` (2–255) | `{"best": "billing", "probabilities": {...}}` |
| `score` | `text`, `question`, `levels` (2–16, lowest first) | `{"best": "high", "expected_level": 1.8, "probabilities": {...}}` |

All three have async versions, used automatically by async agents.

## Usage

```python
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.tools.superion import SuperionToolSpec

agent = FunctionAgent(
    tools=SuperionToolSpec().to_tool_list(),
    llm=OpenAI(model="gpt-5-mini"),
)
await agent.run("Ticket: my card was charged twice for order #4411, fix it today!")
```

Or call it directly:

```python
spec = SuperionToolSpec()
spec.classify("Ticket: my card was charged twice", "Which team should handle it?", ["billing", "tech", "sales"])
# '{"best": "billing", "probabilities": {"billing": 0.98, ...}}'
```

`SuperionToolSpec(api_key=None, model=..., base_url=None, timeout=120.0)` — `api_key` defaults to
`SUPERION_API_KEY`.

## About Superion S1

**#1 of 214 on S1MB English v1 — Task Average 75.06 · Borda 89.82 (12 Nov 2026)** —
[leaderboard](https://huggingface.co/datasets/hotchpotch/s1mb-result).
Calibrated probabilities, one call, no text generation, sub-second, deterministic within a pinned model version. Built on Gemma 4 26B-A4B, INT4 experts.

| Plan | Price |
|---|---|
| Free | 20 M input tokens per day per key, permanent |
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
