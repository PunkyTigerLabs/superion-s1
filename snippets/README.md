# Superion S1 — quickstart snippets

Reusable, tested quickstart snippets for **Superion S1** by Punky Tiger Labs, for the website,
Hugging Face model card / Space, Postman and blog posts. Every snippet sends the same
documented example and was run against the live API on 12 Nov 2026.

| file | use |
|---|---|
| `snippets/QUICKSTART.md` | all-in-one block (curl + Python + JS + response) for web, HF and READMEs |
| `snippets/quickstart.sh` | curl |
| `snippets/quickstart.py` | Python SDK (`pip install superion-s1`) |
| `snippets/quickstart_requests.py` | Python without SDK |
| `snippets/quickstart.mjs` | JS/TS SDK (`npm i @punkytigerlabs/superion-s1`) |
| `snippets/quickstart_fetch.mjs` | JS without SDK (server-side `fetch`) |
| `snippets/response.json` | real response (v6, 12 Nov 2026, rounded to 4 decimals) |

Rules for reuse: cite the ranking with its date and link; say "calibrated probabilities, one call, no text
generation", "sub-second", "0.042 USD per million input tokens, output free", "permanent Free plan".
Never put a real key in a snippet.

## Test

```bash
SUPERION_API_KEY=s1k_... bash tests/test_snippets.sh     # 4-5 real requests
```

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

Snippets are MIT-licensed (see the root `LICENSE`). The Superion S1 model and API are proprietary services of Punky Tiger Labs, Inc.
