# Superion S1 — Postman collection

Postman collection (v2.1) for the **Superion S1** API by Punky Tiger Labs, generated from the
[OpenAPI spec](../openapi/superion-s1.yaml) and enriched with real
examples and test scripts. Ready for the **Postman API Network**.

File: [`superion-s1.postman_collection.json`](superion-s1.postman_collection.json)

| folder | requests |
|---|---|
| Decisions | Support ticket (refund, sentiment, urgency) · Moderation · Lead scoring · Agent guardrail |
| Models | List served models (public) |
| Account | Usage · Rotate key · Revoke key |
| Service | Health (public) |

## Use

1. Get a free key (100 M input tokens/day) at https://punkytigerlabs.com/s1/
2. *Import* the JSON file in Postman.
3. Set the collection variable `apiKey` (or an environment variable with the same name) to your `s1k_…` key.
4. Send *Support ticket*. Each decision request has tests: 200, one answer per question, probabilities in [0, 1], output tokens 0.

Variables: `baseUrl` (`https://api.punkytigerlabs.com`), `model` (v6 by default), `apiKey` (empty).

## Rebuild from the spec

```bash
npx -y -p openapi-to-postmanv2@6.4.3 openapi2postmanv2 -s ../openapi/superion-s1.yaml \
  -o build/raw.json -p -O folderStrategy=Tags,requestParametersResolution=Example,exampleParametersResolution=Example
python3 scripts/build.py build/raw.json superion-s1.postman_collection.json
pytest tests                     # schema v2.1, no embedded key, real bodies, public endpoints without auth
```

Run it headless with Newman: `npx newman run superion-s1.postman_collection.json --env-var apiKey=$SUPERION_API_KEY`
(the key then shows in your process list; prefer a Postman environment file with restricted permissions).

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

This collection is MIT-licensed (see the root `LICENSE`). The Superion S1 model and API are proprietary
services of Punky Tiger Labs, Inc., used under the [API terms](https://punkytigerlabs.com/s1/terms).
