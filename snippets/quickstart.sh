# Superion S1 quickstart (curl). Free key: https://punkytigerlabs.com/s1/
export SUPERION_API_KEY="s1k_..."

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
