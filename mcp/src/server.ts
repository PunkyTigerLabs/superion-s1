/**
 * Superion S1 MCP server: calibrated decisions as tools for AI agents.
 * Tools: decide_yes_no, classify, score, check_action, decide.
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import {
  SuperionClient, SuperionError, VERSION,
  type ChoiceAnswer, type ClientOptions, type DecisionResponse, type NoulAnswer, type Question, type ScoreAnswer,
} from "./api.js";

export { SuperionClient, SuperionError, VERSION } from "./api.js";
export type { ClientOptions, DecisionResponse, Question } from "./api.js";

const ANNOTATIONS = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true } as const;

const text = z.string().min(1).describe(
  "The text the question is about: a message, ticket, document, transcript, or a description of an action and its context. Up to ~32k tokens.",
);

const round = (x: number) => Math.round(x * 1e6) / 1e6;

/** Risk scale used by check_action, lowest first. */
export const RISK_LEVELS = ["no risk", "low risk", "moderate risk", "high risk"];

/** 1 − H(p)/ln(n): 1 when one option holds all the probability, 0 when all are equal. */
function confidence(ps: number[]): number {
  if (ps.length < 2) return 1;
  const h = -ps.reduce((s, p) => (p > 0 ? s + p * Math.log(p) : s), 0);
  return round(Math.max(0, 1 - h / Math.log(ps.length)));
}

function meta(r: DecisionResponse) {
  return {
    model: r.model,
    input_tokens: r.usage?.input_tokens,
    ...(r.meta?.request_id ? { request_id: r.meta.request_id } : {}),
    ...(r.meta?.cost_usd ? { cost_usd: r.meta.cost_usd } : {}),
  };
}

function ok(data: Record<string, unknown>): CallToolResult {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }], structuredContent: data };
}

function fail(e: unknown): CallToolResult {
  const msg = e instanceof SuperionError ? e.message : `Unexpected error: ${(e as Error)?.message ?? String(e)}`;
  return { content: [{ type: "text", text: msg }], isError: true };
}

function answerOf<T>(r: DecisionResponse, id: string, type: string): T {
  const a = r.answers?.[id];
  if (!a || a.type !== type) throw new SuperionError(`Unexpected response from Superion S1: no ${type} answer for "${id}".`);
  return a as T;
}

export interface ServerOptions extends ClientOptions {
  client?: SuperionClient;
}

export function createServer(opts: ServerOptions = {}): McpServer {
  const client = opts.client ?? new SuperionClient(opts);
  const server = new McpServer(
    { name: "superion-s1", title: "Superion S1", version: VERSION },
    {
      instructions:
        "Superion S1 returns calibrated probabilities (not text) for yes/no, choice and score questions about a text, in well under a second. " +
        "Use check_action as a gate before irreversible or external actions (sending, deleting, paying, publishing), and the other tools to triage, moderate, route or score text. " +
        "Because the probabilities are calibrated, a threshold means what it says: e.g. act automatically above 0.8 and ask the user otherwise.",
    },
  );

  server.registerTool(
    "decide_yes_no",
    {
      title: "Decide yes/no (calibrated)",
      description:
        "Calibrated probability that the answer to a yes/no question about a text is YES. " +
        "Use before any irreversible or external action (e.g. 'Does this action do exactly what the user asked?', 'Is this message safe to send?'), " +
        "or whenever you need a reliable yes/no judgement about a text. Returns a probability, not prose; pick your own threshold.",
      inputSchema: {
        text,
        question: z.string().min(1).describe("The yes/no question, written as you would for a careful human reviewer."),
        yes_means: z.string().optional().describe("Optional: what YES means (default 'yes')."),
        no_means: z.string().optional().describe("Optional: what NO means (default 'no')."),
      },
      annotations: ANNOTATIONS,
    },
    async ({ text: state, question, yes_means, no_means }) => {
      try {
        const r = await client.decide(state, {
          q: { type: "noul", instructions: question, criteria: { true: yes_means || "yes", false: no_means || "no" } },
        });
        const p = answerOf<NoulAnswer>(r, "q", "noul").noul;
        return ok({ probability_yes: round(p), answer: p >= 0.5 ? "yes" : "no", ...meta(r) });
      } catch (e) {
        return fail(e);
      }
    },
  );

  server.registerTool(
    "classify",
    {
      title: "Classify into one label (calibrated)",
      description:
        "Pick the most likely label for a text from 2 to 255 labels, with a calibrated probability per label. " +
        "Use for sentiment, intent, topic, routing (e.g. which team or model should handle this), moderation categories. Returns probabilities, not prose.",
      inputSchema: {
        text,
        question: z.string().min(1).describe("What to decide, e.g. 'Which team should handle this ticket?'."),
        labels: z.array(z.string().min(1)).min(2).max(255).describe("Candidate labels (2 to 255, unique). The answer is one of these."),
        descriptions: z
          .record(z.string(), z.string())
          .optional()
          .describe("Optional: label → longer description of when it applies. Improves accuracy for ambiguous labels."),
      },
      annotations: ANNOTATIONS,
    },
    async ({ text: state, question, labels, descriptions }) => {
      try {
        if (new Set(labels).size !== labels.length) throw new SuperionError("labels must be unique.");
        const criteria = Object.fromEntries(labels.map((l) => [l, descriptions?.[l] || l]));
        const r = await client.decide(state, { q: { type: "choice", instructions: question, criteria } });
        const a = answerOf<ChoiceAnswer>(r, "q", "choice");
        const ranked = Object.entries(a.probabilities).sort((x, y) => y[1] - x[1]);
        const best = a.choice ?? ranked[0][0];
        return ok({
          label: best,
          probability: round(a.probabilities[best] ?? ranked[0][1]),
          confidence: round(a.confidence ?? confidence(ranked.map(([, p]) => p))),
          probabilities: Object.fromEntries(ranked.map(([k, p]) => [k, round(p)])),
          ...meta(r),
        });
      } catch (e) {
        return fail(e);
      }
    },
  );

  server.registerTool(
    "score",
    {
      title: "Score on an ordered scale (calibrated)",
      description:
        "Rate a text on an ordered scale of 2 to 16 levels (lowest first), e.g. urgency, risk, lead quality, toxicity. " +
        "Returns the most likely level, the expected level, a 0–1 normalized score and a calibrated probability per level.",
      inputSchema: {
        text,
        question: z.string().min(1).describe("What to rate, e.g. 'How urgent is a reply?'."),
        levels: z
          .array(z.string().min(1))
          .min(2)
          .max(16)
          .describe("Ordered level descriptions, LOWEST FIRST, e.g. ['not urgent', 'somewhat urgent', 'very urgent']."),
      },
      annotations: ANNOTATIONS,
    },
    async ({ text: state, question, levels }) => {
      try {
        const r = await client.decide(state, { q: { type: "score", instructions: question, criteria: levels } });
        const a = answerOf<ScoreAnswer>(r, "q", "score");
        const ps = levels.map((_, i) => a.probabilities[String(i)] ?? 0);
        const bestIdx = ps.indexOf(Math.max(...ps));
        const expected = a.score ?? ps.reduce((s, p, i) => s + i * p, 0);
        return ok({
          level: levels[bestIdx],
          level_index: bestIdx,
          probability: round(ps[bestIdx]),
          expected_level: round(expected),
          normalized_score: round(levels.length > 1 ? expected / (levels.length - 1) : 0),
          confidence: round(a.confidence ?? confidence(ps)),
          probabilities: Object.fromEntries(levels.map((l, i) => [l, round(ps[i])])),
          ...meta(r),
        });
      } catch (e) {
        return fail(e);
      }
    },
  );

  server.registerTool(
    "check_action",
    {
      title: "Check an action before doing it (calibrated guardrail)",
      description:
        "Call BEFORE any irreversible or external action (deleting, sending, paying, publishing, deploying, writing to production). " +
        "In one call returns: the probability that the planned action does what the user asked (matches_request), " +
        "the probability that it is irreversible, and its risk level on a 4-level scale. " +
        "Returns probabilities, not a verdict: you choose the thresholds (e.g. proceed only if matches_request ≥ 0.8 and the action is not high risk; otherwise ask the user).",
      inputSchema: {
        action: z.string().min(1).describe("The action you are about to take, concretely (tool, target, parameters), e.g. 'Delete the folder /reports and all its files'."),
        context: z.string().min(1).describe("What the user asked for, ideally in their own words, plus any relevant constraints."),
      },
      annotations: ANNOTATIONS,
    },
    async ({ action, context }) => {
      try {
        const state = `User request:\n${context}\n\nPlanned action:\n${action}`;
        const r = await client.decide(state, {
          matches_request: {
            type: "noul",
            instructions: "Does the planned action do what the user asked, without going beyond it?",
            criteria: { true: "yes, it does what the user asked", false: "no, it does something different or more than asked" },
          },
          irreversible: {
            type: "noul",
            instructions: "Would the planned action be hard or impossible to undo once executed?",
            criteria: { true: "irreversible", false: "can be undone" },
          },
          risk: { type: "score", instructions: "How risky is the planned action for the user?", criteria: RISK_LEVELS },
        });
        const m = answerOf<NoulAnswer>(r, "matches_request", "noul").noul;
        const irr = answerOf<NoulAnswer>(r, "irreversible", "noul").noul;
        const risk = answerOf<ScoreAnswer>(r, "risk", "score");
        const ps = RISK_LEVELS.map((_, i) => risk.probabilities[String(i)] ?? 0);
        const bestIdx = ps.indexOf(Math.max(...ps));
        const expected = risk.score ?? ps.reduce((s, p, i) => s + i * p, 0);
        return ok({
          matches_request: round(m),
          irreversible: round(irr),
          risk: {
            level: RISK_LEVELS[bestIdx],
            probability: round(ps[bestIdx]),
            expected_level: round(expected),
            normalized_score: round(expected / (RISK_LEVELS.length - 1)),
            probabilities: Object.fromEntries(RISK_LEVELS.map((l, i) => [l, round(ps[i])])),
          },
          ...meta(r),
        });
      } catch (e) {
        return fail(e);
      }
    },
  );

  const question = z.discriminatedUnion("type", [
    z.object({
      type: z.literal("noul"),
      instructions: z.string().min(1),
      criteria: z.object({ true: z.string(), false: z.string() }).describe("What true and false mean, e.g. {true: 'yes', false: 'no'}."),
    }),
    z.object({
      type: z.literal("choice"),
      instructions: z.string().min(1),
      criteria: z.record(z.string(), z.string()).describe("Option id → description, 2 to 255 options."),
    }),
    z.object({
      type: z.literal("score"),
      instructions: z.string().min(1),
      criteria: z.array(z.string()).min(2).max(16).describe("Ordered level descriptions, lowest first (2 to 16)."),
    }),
  ]);

  server.registerTool(
    "decide",
    {
      title: "Decide several questions at once (calibrated)",
      description:
        "Ask any number of typed questions about one text in a single call (the text is billed once). " +
        "Each question is 'noul' (yes/no → probability of true), 'choice' (one of 2–255 options → probability per option) " +
        "or 'score' (ordered scale of 2–16 levels, lowest first → probability per level index). " +
        "Use it to triage a ticket (refund? sentiment? urgency?) or to gate an action on several checks at once. Returns probabilities, not prose.",
      inputSchema: {
        text,
        questions: z
          .record(z.string(), question)
          .describe(
            "Map of your question id → question. Example: {\"refund\": {\"type\": \"noul\", \"instructions\": \"Does the customer ask for a refund?\", \"criteria\": {\"true\": \"yes\", \"false\": \"no\"}}, " +
              "\"urgency\": {\"type\": \"score\", \"instructions\": \"How urgent is a reply?\", \"criteria\": [\"not urgent\", \"somewhat urgent\", \"very urgent\"]}}",
          ),
      },
      annotations: ANNOTATIONS,
    },
    async ({ text: state, questions }) => {
      try {
        const ids = Object.keys(questions);
        if (!ids.length) throw new SuperionError("questions must contain at least one question.");
        for (const id of ids) {
          const q = questions[id] as Question;
          if (q.type === "choice") {
            const n = Object.keys(q.criteria).length;
            if (n < 2 || n > 255) throw new SuperionError(`question "${id}": choice needs 2 to 255 options.`);
          }
        }
        const r = await client.decide(state, questions as Record<string, Question>);
        return ok({ answers: r.answers, ...meta(r) });
      } catch (e) {
        return fail(e);
      }
    },
  );

  return server;
}
