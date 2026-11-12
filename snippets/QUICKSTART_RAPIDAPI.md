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
  "usage": {"input_tokens": 135, "output_tokens": 0},
  "answers": {
    "refund":    {"type": "noul",   "noul": 0.9997},
    "sentiment": {"type": "choice", "probabilities": {"pos": 0.0003, "neg": 0.9943, "neu": 0.0054}},
    "urgency":   {"type": "score",  "probabilities": {"0": 0.0000, "1": 0.1922, "2": 0.8078}}
  }
}
```
