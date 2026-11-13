# @punkytigerlabs/superion-s1

JavaScript / TypeScript client for **Superion S1** by Punky Tiger Labs — a calibrated decision
API. Send a text and typed questions (yes/no, choice, score); get one calibrated probability
distribution per question in a single call, with no text generation.

Zero dependencies (uses `fetch`), ESM + CommonJS, full types. Node ≥ 20, Bun, Deno, edge
runtimes. **Server-side only:** the API sends no CORS headers, so your key never lives in a web page.

```bash
npm install @punkytigerlabs/superion-s1
export SUPERION_API_KEY=s1k_...   # free key: https://punkytigerlabs.com/s1/
```

## Quickstart

```ts
import { Superion, noul, choice, score } from "@punkytigerlabs/superion-s1";

const s1 = new Superion(); // reads SUPERION_API_KEY

const d = await s1.decide(
  "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
  {
    refund: noul("Does the customer ask for a refund or a replacement?"),
    sentiment: choice("Overall sentiment of the message.", { pos: "positive", neg: "negative", neu: "neutral" }),
    urgency: score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
  },
);

d.answers.refund.p;            // 0.9998  — typed as NoulAnswer
d.answers.sentiment.best;      // "neg"   — ChoiceAnswer
d.answers.urgency.bestLabel;   // "very urgent" — ScoreAnswer (.expected, .normalized)
d.usage.inputTokens;           // 135 billed tokens; output is always 0
```

CommonJS: `const { Superion } = require("@punkytigerlabs/superion-s1");`

Single question shortcuts:

```ts
const p = await s1.noul(text, "Is this message spam?");                     // number
const c = await s1.choice(text, "Which team?", ["billing", "tech", "sales"]); // .best .p .ranked()
const s = await s1.score(text, "Toxicity?", ["none", "mild", "severe"]);      // .best .expected
```

## Question types

| builder | criteria | answer |
|---|---|---|
| `noul(instructions, { true, false })` | what `true` / `false` mean (default yes/no) | `NoulAnswer.p` = probability of `true` |
| `choice(instructions, options)` | `{ id: description }` or `string[]` (2–255) | `ChoiceAnswer.probabilities`, `.best`, `.p` |
| `score(instructions, levels)` | 2–16 ordered levels, lowest first | `ScoreAnswer.probabilities[i]`, `.best`, `.bestLabel`, `.expected`, `.normalized` |

## Options

```ts
new Superion({
  apiKey,                  // default process.env.SUPERION_API_KEY
  model,                   // default "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc" (or SUPERION_MODEL)
  baseURL,                 // default "https://api.punkytigerlabs.com"
  timeout: 120_000,        // ms — a large state can wait up to ~70 s in the fair queue
  maxRetries: 2,           // 429, 5xx, network errors; honours Retry-After
  maxRetryWait: 60_000,    // a longer Retry-After (e.g. daily quota) throws at once
  fetch,                   // custom fetch
});
```

Also: `s1.models()`, `s1.usage()`, `s1.health()`, `s1.rotateKey()`, `s1.revokeKey()`.
`d.rateLimit` holds the `x-ratelimit-*` headers; `d.balanceUsd` the Prepaid balance after the call.

## Errors

`BadRequestError` (400) · `AuthenticationError` (401) · `InsufficientBalanceError` (402, `.balanceUsd`) ·
`RequestTooLargeError` (413) · `UnprocessableError` (422) · `RateLimitError` (429, `.retryAfter`) ·
`ServiceUnavailableError` (503) · `APIConnectionError` / `APITimeoutError`. All extend `SuperionError`;
HTTP ones expose `.status`, `.error` and `.body`. Failed requests are never charged.

## Development

```bash
npm install
npm test               # offline, mocked fetch
npm run build          # dist/ (ESM + CJS + .d.ts)
S1_LIVE=1 SUPERION_API_KEY=s1k_... npm run test:live
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

This client is MIT-licensed (see `LICENSE`). The Superion S1 model and API are proprietary
services of Punky Tiger Labs, Inc., used under the [API terms](https://punkytigerlabs.com/s1/terms).
