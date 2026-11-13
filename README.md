# Superion S1

**Calibrated decisions in one API call.** Send a text and typed questions (yes/no, choice, score) and get
one calibrated probability per question, without generating text, in well under a second.

**#1 of 214 on S1MB English v1 — Task Average 75.06 · Borda 89.82 (12 Nov 2026)** ·
[leaderboard](https://huggingface.co/datasets/hotchpotch/s1mb-result)

[Website](https://punkytigerlabs.com/s1/) · [Docs](https://punkytigerlabs.com/s1/docs) ·
[Use cases](https://punkytigerlabs.com/s1/use-cases) ·
[Model card](https://huggingface.co/PunkyTiger/Superion-S1) ·
[Live demo](https://huggingface.co/spaces/ZamnaMx/superion-s1-demo) ·
[Status](https://punkytigerlabs.com/s1/status)

Built by [Punky Tiger Labs](https://punkytigerlabs.com) on Gemma 4 26B-A4B, INT4 experts.

```
"Message: The laptop arrived broken. I want my money back now, this is unacceptable."
  refund     (yes/no)  ->  0.9998
  sentiment  (choice)  ->  neg 0.994 · neu 0.006 · pos 0.000
  urgency    (score)   ->  very urgent 0.94 · somewhat urgent 0.06 · not urgent 0.00
```

Use it to triage tickets, moderate content, score leads, route prompts to the right LLM or decide
whether an agent may run a tool call. Because the probabilities are calibrated, a threshold means what
it says: route automatically above 0.8 and send the rest to a person.

## Quickstart

Get a free key (20 M input tokens per day, permanent) at https://punkytigerlabs.com/s1/

```bash
curl https://api.punkytigerlabs.com/v1/systemone \
  -H "Authorization: Bearer $SUPERION_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
       "state": "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
       "questions": {
         "refund":    {"type": "noul",   "instructions": "Does the customer ask for a refund or a replacement?", "criteria": {"true": "yes", "false": "no"}},
         "sentiment": {"type": "choice", "instructions": "Overall sentiment of the message.", "criteria": {"pos": "positive", "neg": "negative", "neu": "neutral"}},
         "urgency":   {"type": "score",  "instructions": "How urgent is a reply?", "criteria": ["not urgent", "somewhat urgent", "very urgent"]}}}'
```

Python

```python
from superion_s1 import Superion, noul, choice, score   # pip install superion-s1

d = Superion().decide("Message: The laptop arrived broken. I want my money back now.", {
    "refund":    noul("Does the customer ask for a refund or a replacement?"),
    "sentiment": choice("Overall sentiment of the message.", {"pos": "positive", "neg": "negative", "neu": "neutral"}),
    "urgency":   score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
})
d["refund"].p, d["sentiment"].best, d["urgency"].best_label
```

JavaScript / TypeScript

```ts
import { Superion, noul } from "@punkytigerlabs/superion-s1";   // npm i @punkytigerlabs/superion-s1

const p = await new Superion().noul("Message: I want my money back.", "Does the customer ask for a refund?");
```

## What is in this repository

| folder | package | what |
|---|---|---|
| [`python/`](python) | `superion-s1` | Python SDK: sync + async, typed answers, retries, `noul()`, `choice()`, `score()`, `decide()` |
| [`js/`](js) | `@punkytigerlabs/superion-s1` | JavaScript / TypeScript SDK: `fetch`, ESM + CJS, no dependencies |
| [`integrations/langchain/`](integrations/langchain) | `langchain-superion` | LangChain tool, guardrail and router |
| [`integrations/llamaindex/`](integrations/llamaindex) | `llama-index-tools-superion` | LlamaIndex tool spec |
| [`openapi/`](openapi) | | OpenAPI 3.1 spec (full, and a marketplace variant) |
| [`postman/`](postman) | | Postman collection with examples and tests |
| [`notebooks/`](notebooks) | | Colab: *Calibrated ticket triage in 10 lines* |
| [`snippets/`](snippets) | | Tested quickstart snippets (curl, Python, JS) |

The n8n community node lives in its own repository:
[PunkyTigerLabs/n8n-nodes-superion-s1](https://github.com/PunkyTigerLabs/n8n-nodes-superion-s1).

## Question types

| type | criteria | answer |
|---|---|---|
| `noul` | what `true` and `false` mean | probability of `true` |
| `choice` | 2–255 options, `id -> description` | probability per option |
| `score` | 2–16 ordered levels, lowest first | probability per level index |

Ask any number of questions about the same text in one call: the text is billed once, each question adds
only its own tokens. Up to 32,768 tokens per question and 65,536 per request; longer inputs are refused,
never truncated. Full reference: https://punkytigerlabs.com/s1/docs

## Pricing

| Plan | Price |
|---|---|
| Free | 20 M input tokens per day per key, permanent |
| Prepaid | 0.042 USD per million input tokens, output free |
| Contract | dedicated key, price on request |

## Custom & industry models

Punky Tiger Labs also builds custom and industry-specific decision models — fitted to your own
taxonomy, labels and data, for a specific industry or objective — served on a dedicated instance.
Contact: [alvaro.lopez@punkytigerlabs.com](mailto:alvaro.lopez@punkytigerlabs.com).

## Development

Each folder has its own README and tests. Offline tests need no key; live tests run with
`S1_LIVE=1 SUPERION_API_KEY=s1k_...`. CI runs every folder on each push.

## License

The code in this repository is MIT-licensed (see [`LICENSE`](LICENSE)). The Superion S1 model and the
service behind `api.punkytigerlabs.com` are proprietary services of Punky Tiger Labs, Inc., used under the
[API terms](https://punkytigerlabs.com/s1/terms).
