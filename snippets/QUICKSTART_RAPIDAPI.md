# Superion S1 on RapidAPI — Quickstart (template)

<!-- Fill RAPIDAPI_HOST after the listing exists. RapidAPI forwards to api.punkytigerlabs.com with its own
     contract key; the request body and response are identical to the direct API. -->

```bash
curl --request POST \
  --url https://RAPIDAPI_HOST/v1/systemone \
  --header "Content-Type: application/json" \
  --header "X-RapidAPI-Host: RAPIDAPI_HOST" \
  --header "X-RapidAPI-Key: $RAPIDAPI_KEY" \
  --data '{"model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
          "state": "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
          "questions": {"refund": {"type": "noul", "instructions": "Does the customer ask for a refund or a replacement?",
                                   "criteria": {"true": "yes", "false": "no"}}}}'
```

```python
import os, requests
r = requests.post("https://RAPIDAPI_HOST/v1/systemone", timeout=120,
    headers={"X-RapidAPI-Key": os.environ["RAPIDAPI_KEY"], "X-RapidAPI-Host": "RAPIDAPI_HOST"},
    json={"model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc", "state": "Message: …",
          "questions": {"refund": {"type": "noul", "instructions": "Does the customer ask for a refund?",
                                   "criteria": {"true": "yes", "false": "no"}}}})
print(r.json()["answers"])
```

Response:

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
