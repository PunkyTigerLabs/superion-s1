# superion-s1

Python client for **Superion S1** by Punky Tiger Labs — a calibrated decision API. Send a text
and typed questions (yes/no, choice, score); get one calibrated probability distribution per
question in a single call, with no text generation.

```bash
pip install superion-s1
export SUPERION_API_KEY=s1k_...   # free key: https://punkytigerlabs.com/s1/
```

## Quickstart

```python
from superion_s1 import Superion, noul, choice, score

s1 = Superion()  # reads SUPERION_API_KEY

d = s1.decide(
    "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
    {
        "refund":    noul("Does the customer ask for a refund or a replacement?"),
        "sentiment": choice("Overall sentiment of the message.",
                            {"pos": "positive", "neg": "negative", "neu": "neutral"}),
        "urgency":   score("How urgent is a reply?",
                           ["not urgent", "somewhat urgent", "very urgent"]),
    },
)

d["refund"].p             # 0.9998  probability of "true"
d["sentiment"].best       # "neg"
d["sentiment"].probabilities  # {"pos": 0.0003, "neg": 0.9943, "neu": 0.0054}
d["urgency"].best_label   # "very urgent"
d["urgency"].expected     # 1.81   expected level index (0..2)
d.usage.input_tokens      # 135    billed tokens; output is always 0
```

One question? Use the shortcuts:

```python
p = s1.noul(text, "Is this message spam?")                 # float
c = s1.choice(text, "Which team?", ["billing", "tech", "sales"])   # .best, .p, .ranked()
s = s1.score(text, "Toxicity?", ["none", "mild", "severe"])        # .best, .expected, .normalized
```

### Async

```python
import asyncio
from superion_s1 import AsyncSuperion, noul

async def main():
    async with AsyncSuperion() as s1:
        results = await asyncio.gather(*[
            s1.noul(t, "Does the customer ask for a refund?") for t in tickets
        ])

asyncio.run(main())
```

## Question types

| builder | criteria | answer |
|---|---|---|
| `noul(instructions, true="yes", false="no")` | what `true` / `false` mean | `NoulAnswer.p` = probability of `true` |
| `choice(instructions, options)` | dict `id → description` or list of labels (2–255) | `ChoiceAnswer.probabilities`, `.best`, `.p` |
| `score(instructions, levels)` | 2–16 ordered levels, lowest first | `ScoreAnswer.probabilities` by index, `.best`, `.best_label`, `.expected`, `.normalized` |

Write instructions and criteria as you would for a careful human reviewer: answers depend on
the wording. Asking more questions about the same state only adds the questions' own tokens
(the state is billed once per request).

## Configuration

| argument | env var | default |
|---|---|---|
| `api_key` | `SUPERION_API_KEY` | — (required) |
| `model` | `SUPERION_MODEL` | `superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc` |
| `base_url` | `SUPERION_BASE_URL` | `https://api.punkytigerlabs.com` |
| `timeout` | | `120` s (a large state can wait up to ~70 s in the fair queue) |
| `max_retries` | | `2` (429, 5xx, connection errors; honours `Retry-After`) |
| `max_retry_wait` | | `60` s — a longer `Retry-After` (e.g. daily quota) raises at once |

Model IDs are immutable; `s1.models()` lists what is served. Other endpoints:
`s1.usage()` (plan, counters, Prepaid balance), `s1.health()`, `s1.rotate_key()`, `s1.revoke_key()`.
Rate-limit headers are on `d.rate_limit`; Prepaid balance after the call on `d.balance_usd`.

## Errors

All errors inherit from `superion_s1.SuperionError`.

| status | exception | what to do |
|---|---|---|
| 400 | `BadRequestError` | fix the request (message says what) |
| 401 | `AuthenticationError` | check the key |
| 402 | `InsufficientBalanceError` (`.balance_usd`) | add credits |
| 413 | `RequestTooLargeError` | body over 4 MB: split it |
| 422 | `UnprocessableError` | over 32,768 tokens per question / 65,536 per request, or too many options/levels |
| 429 | `RateLimitError` (`.retry_after`) | quota, per-minute limit or queue full |
| 503 | `ServiceUnavailableError` (`.retry_after`) | retried automatically |
| — | `APIConnectionError`, `APITimeoutError` | network |

Failed requests are never charged. The API refuses over-long inputs with 422; it never truncates.

## Examples

See [`examples/`](examples): ticket triage, moderation, an LLM router and an agent guardrail.

## Development

```bash
pip install -e ".[dev]"
pytest                                   # offline, mocked
S1_LIVE=1 SUPERION_API_KEY=s1k_... pytest tests/test_live.py   # 2 real calls
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
