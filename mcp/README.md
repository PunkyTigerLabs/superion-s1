# Superion S1 MCP server

<!-- mcp-name: io.github.PunkyTigerLabs/superion-s1 -->

**Calibrated decisions for AI agents.** Give your agent a fast, calibrated "should I?" before it acts.
Superion S1 answers yes/no, choice and score questions about any text with **probabilities, not prose**,
in well under a second.

**#1 of 214 on S1MB English v1 — Task Average 75.06 · Borda 89.82 (12 Nov 2026)** ·
[leaderboard](https://huggingface.co/datasets/hotchpotch/s1mb-result)

```
Agent plans: delete the folder /reports.   User asked: archive last month reports.
decide_yes_no("Does the planned action do exactly what the user asked?")  ->  probability_yes 0.006
```

Because the probabilities are calibrated, a threshold means what it says: act automatically above 0.8,
ask the user otherwise.

## Get a key

Free key, **20 M input tokens per day, permanent**: https://punkytigerlabs.com/s1/

## Tools

| tool | what it does | returns |
|---|---|---|
| `decide_yes_no` | Probability that the answer to a yes/no question about a text is yes. Use it as a gate before irreversible or external actions. | `probability_yes`, `answer` |
| `classify` | Pick one of 2–255 labels (sentiment, intent, topic, routing, moderation). Optional per-label descriptions. | `label`, `probability`, `confidence`, `probabilities` |
| `score` | Rate a text on an ordered scale of 2–16 levels, lowest first (urgency, risk, lead quality). | `level`, `expected_level`, `normalized_score`, `confidence`, `probabilities` |
| `decide` | Any number of typed questions (`noul`, `choice`, `score`) about one text in one call; the text is billed once. | `answers` (raw API format) |

Every result also carries `model`, `input_tokens` and `request_id`. All tools are read-only.
Output tokens are always 0 and free.

## Configuration

The server runs locally over **stdio** with `npx` (Node.js 18 or later). It only needs your key in
`SUPERION_API_KEY`.

### Claude Desktop

Settings → Developer → Edit Config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "superion-s1": {
      "command": "npx",
      "args": ["-y", "@punkytigerlabs/superion-s1-mcp"],
      "env": { "SUPERION_API_KEY": "s1k_your_key" }
    }
  }
}
```

Restart Claude Desktop. The four tools appear under the tools menu.

### Claude Code

```bash
claude mcp add superion-s1 --env SUPERION_API_KEY=s1k_your_key -- npx -y @punkytigerlabs/superion-s1-mcp
```

### Cursor

`~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one project):

```json
{
  "mcpServers": {
    "superion-s1": {
      "command": "npx",
      "args": ["-y", "@punkytigerlabs/superion-s1-mcp"],
      "env": { "SUPERION_API_KEY": "s1k_your_key" }
    }
  }
}
```

### VS Code (GitHub Copilot agent mode)

`.vscode/mcp.json`. VS Code prompts for the key once and stores it securely:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "superion-api-key",
      "description": "Superion S1 API key",
      "password": true
    }
  ],
  "servers": {
    "superion-s1": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@punkytigerlabs/superion-s1-mcp"],
      "env": { "SUPERION_API_KEY": "${input:superion-api-key}" }
    }
  }
}
```

### Environment variables

| variable | required | default |
|---|---|---|
| `SUPERION_API_KEY` | yes | — |
| `SUPERION_MODEL` | no | `superion-s1-latest` (pin a version such as `superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc` for reproducible results) |
| `SUPERION_BASE_URL` | no | `https://api.punkytigerlabs.com` |

Keep your key in the client config or a secret store, never in a shared repository. On Windows, if
`npx` is not found, use `"command": "cmd", "args": ["/c", "npx", "-y", "@punkytigerlabs/superion-s1-mcp"]`.

## Examples

Ask your agent things like:

- "Before sending that email, check with Superion whether it answers what the customer asked."
- "Classify these 20 tickets by team (billing, tech, sales) and give me only the ones below 0.8 confidence."
- "Score each lead's buying intent from 'none' to 'ready to buy'."

`decide` with several questions:

```json
{
  "text": "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
  "questions": {
    "refund":    {"type": "noul",   "instructions": "Does the customer ask for a refund or a replacement?", "criteria": {"true": "yes", "false": "no"}},
    "sentiment": {"type": "choice", "instructions": "Overall sentiment of the message.", "criteria": {"pos": "positive", "neg": "negative", "neu": "neutral"}},
    "urgency":   {"type": "score",  "instructions": "How urgent is a reply?", "criteria": ["not urgent", "somewhat urgent", "very urgent"]}
  }
}
```

→ `refund` 0.9998 · `sentiment` neg 0.994 · `urgency` expected level 1.94 of 2.

## Errors

Errors come back as tool errors (`isError: true`) with a message the agent can act on:

| status | meaning |
|---|---|
| no key | `SUPERION_API_KEY` is not set; the message says where to get one |
| 401 | the key was rejected; check it or get a new one |
| 402 | prepaid balance exhausted; the message includes the balance and where to add credits |
| 429 | rate limit or daily quota; the message includes `Retry-After` |
| 413 / 422 | text too long (max 32,768 tokens per question; inputs are never truncated) |
| other 4xx | the server's own explanation of what to fix |
| 5xx | temporary service error; see https://punkytigerlabs.com/s1/status |

Short `Retry-After` waits (≤ 10 s) on 429/502/503/504 are retried automatically, up to twice.
Failed requests are not charged.

## Privacy

The server is a thin client: it sends the text and questions you pass to `https://api.punkytigerlabs.com`
with your key and returns the answer. Nothing is stored locally. See https://punkytigerlabs.com/s1/privacy.

## Development

```bash
npm install
npm test                                  # build + mock tests + stdio end-to-end
S1_LIVE=1 SUPERION_API_KEY=... npm run test:live   # real API, four tools over stdio
npx @modelcontextprotocol/inspector node dist/index.js
```

## Custom and industry models

Need decisions tuned to your domain, criteria and data? Talk to us: alvaro.lopez@punkytigerlabs.com

## License

MIT © Punky Tiger Labs, Inc. The Superion S1 API is a separate, proprietary service:
[terms](https://punkytigerlabs.com/s1/terms).
