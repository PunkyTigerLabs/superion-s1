# Superion S1 notebooks

| notebook | open |
|---|---|
| **Calibrated ticket triage in 10 lines** — route tickets to a team, rate urgency, flag refunds, and send only the uncertain ones to a human | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/PunkyTigerLabs/superion-s1/blob/main/notebooks/calibrated_ticket_triage.ipynb) |

The notebook uses your own **free key** (100 M input tokens per day): get it at
https://punkytigerlabs.com/s1/ and store it in Colab as the secret `SUPERION_API_KEY`.
6 tickets × 3 decisions use about 900 input tokens.

## Test

```bash
pip install superion-s1 pandas nbclient nbformat ipykernel pytest
pytest tests                                                # structure, no outputs, no keys
S1_LIVE=1 SUPERION_API_KEY=s1k_... pytest tests             # runs the notebook end to end (6 requests)
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

This client is MIT-licensed (see the root `LICENSE`). The Superion S1 model and API are proprietary
services of Punky Tiger Labs, Inc., used under the [API terms](https://punkytigerlabs.com/s1/terms).
