# Superion S1 — Quickstart

Calibrated decisions in one call: ask yes/no (`noul`), `choice` and `score` questions about any text and get
one calibrated probability per question, without text generation (sub-second).

**#1 of 214 on S1MB English v1 — Task Average 75.06 · Borda 89.82 (12 Nov 2026)** —
[leaderboard](https://huggingface.co/datasets/hotchpotch/s1mb-result)

1. Get a free key (20 M input tokens per day): https://punkytigerlabs.com/s1/
2. Call the API:

### curl

```bash
curl https://api.punkytigerlabs.com/v1/systemone \
  -H "Authorization: Bearer $SUPERION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
    "state": "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
    "questions": {
      "refund":    {"type": "noul",   "instructions": "Does the customer ask for a refund or a replacement?", "criteria": {"true": "yes", "false": "no"}},
      "sentiment": {"type": "choice", "instructions": "Overall sentiment of the message.", "criteria": {"pos": "positive", "neg": "negative", "neu": "neutral"}},
      "urgency":   {"type": "score",  "instructions": "How urgent is a reply?", "criteria": ["not urgent", "somewhat urgent", "very urgent"]}
    }
  }'
```

### Python

```bash
pip install superion-s1
```

```python
# Superion S1 quickstart (Python SDK). pip install superion-s1
# Free key: https://punkytigerlabs.com/s1/  ->  export SUPERION_API_KEY=s1k_...
from superion_s1 import Superion, noul, choice, score

s1 = Superion()
d = s1.decide(
    "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
    {
        "refund": noul("Does the customer ask for a refund or a replacement?"),
        "sentiment": choice("Overall sentiment of the message.", {"pos": "positive", "neg": "negative", "neu": "neutral"}),
        "urgency": score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
    },
)
print(d["refund"].p, d["sentiment"].best, d["urgency"].best_label)   # 0.9998 neg very urgent
```

### JavaScript / TypeScript

```bash
npm install @punkytigerlabs/superion-s1
```

```js
// Superion S1 quickstart (Node.js / TypeScript). npm install @punkytigerlabs/superion-s1
// Free key: https://punkytigerlabs.com/s1/  ->  export SUPERION_API_KEY=s1k_...
import { Superion, noul, choice, score } from "@punkytigerlabs/superion-s1";

const s1 = new Superion();
const d = await s1.decide(
  "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
  {
    refund: noul("Does the customer ask for a refund or a replacement?"),
    sentiment: choice("Overall sentiment of the message.", { pos: "positive", neg: "negative", neu: "neutral" }),
    urgency: score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
  },
);
console.log(d.answers.refund.p, d.answers.sentiment.best, d.answers.urgency.bestLabel); // 0.9998 neg very urgent
```

### Response

```json
{
  "model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
  "answers": {
    "refund":    {"type": "noul",   "noul": 0.9998},
    "sentiment": {"type": "choice", "choice": "neg", "confidence": 0.9661, "probabilities": {"pos": 0.0003, "neg": 0.9941, "neu": 0.0056}},
    "urgency":   {"type": "score",  "score": 1.9393, "confidence": 0.7917, "probabilities": {"0": 0.0000, "1": 0.0607, "2": 0.9393},
                  "legend": {"0": "not urgent", "1": "somewhat urgent", "2": "very urgent"}}
  },
  "usage": {"input_tokens": 135, "output_tokens": 0},
  "meta": {"request_id": "63a6718e-ab64-404b-92f3-fdba826d0dfe", "mode": "live", "latency_ms": 103}
}
```

`noul` is the probability of `true`. `choice` and `score` give a probability per option / level
(score levels are indexed in the order you list them, lowest first). Billed input tokens = the state once
+ every question; output is always 0 and free.

**Pricing.** Free: 20 M input tokens/day per key, permanent · Prepaid: 0.042 USD per million input
tokens, output free · Contract: dedicated key.
Docs: https://punkytigerlabs.com/s1/docs · Built on Gemma 4 26B-A4B, INT4 experts.

**Custom & industry models.** Punky Tiger Labs also builds custom and industry-specific decision models,
fitted to your own taxonomy, labels and data, served on a dedicated instance. Contact:
alvaro.lopez@punkytigerlabs.com
