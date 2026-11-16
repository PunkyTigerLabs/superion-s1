/**
 * Minimal Superion S1 HTTP client used by the MCP server (fetch only, no dependencies).
 * API reference: https://punkytigerlabs.com/s1/docs
 */

export const VERSION = "0.1.0";
export const DEFAULT_BASE_URL = "https://api.punkytigerlabs.com";
export const KEY_URL = "https://punkytigerlabs.com/s1/";

export interface NoulQuestion { type: "noul"; instructions: string; criteria: { true: string; false: string } }
export interface ChoiceQuestion { type: "choice"; instructions: string; criteria: Record<string, string> }
export interface ScoreQuestion { type: "score"; instructions: string; criteria: string[] }
export type Question = NoulQuestion | ChoiceQuestion | ScoreQuestion;

export interface NoulAnswer { type: "noul"; noul: number }
export interface ChoiceAnswer { type: "choice"; choice?: string; confidence?: number; probabilities: Record<string, number> }
export interface ScoreAnswer {
  type: "score"; score?: number; confidence?: number; probabilities: Record<string, number>; legend?: Record<string, string>;
}
export type Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer;

export interface DecisionResponse {
  model: string;
  answers: Record<string, Answer>;
  usage: { input_tokens: number; output_tokens: number };
  meta?: { request_id?: string; latency_ms?: number; cost_usd?: string; [k: string]: unknown };
}

export interface ClientOptions {
  apiKey?: string;
  baseURL?: string;
  model?: string;
  /** Milliseconds. Default 120 000 (a large state can wait in the fair queue). */
  timeout?: number;
  /** Retries on 429/502/503/504 and network errors when the wait is short. Default 2. */
  maxRetries?: number;
  fetch?: typeof fetch;
}

/** Error with a message written for the agent (and the human reading its log). */
export class SuperionError extends Error {
  override name = "SuperionError";
  constructor(message: string, readonly status?: number, readonly requestId?: string) {
    super(message);
  }
}

const RETRYABLE = new Set([429, 502, 503, 504]);
const MAX_RETRY_WAIT_MS = 10_000;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function errorMessage(status: number, body: unknown, headers: Headers): string {
  const b = (body && typeof body === "object" ? body : {}) as Record<string, unknown>;
  const detail = typeof b.error === "string" ? b.error : typeof body === "string" && body ? body.slice(0, 300) : "";
  const rid = headers.get("x-request-id");
  const tail = (detail ? ` Server said: ${detail}` : "") + (rid ? ` (request id ${rid})` : "");
  switch (status) {
    case 401:
      return `Superion S1 rejected the API key (401). Check SUPERION_API_KEY in your MCP client config. Get a free key (20 M tokens/day) at ${KEY_URL}.${tail}`;
    case 402: {
      const bal = typeof b.balance_usd === "number" ? ` Balance: ${b.balance_usd} USD.` : "";
      const url = typeof b.contact_url === "string" ? b.contact_url : `${KEY_URL}account`;
      return `Superion S1: insufficient prepaid credit (402).${bal} Add credits at ${url}.${tail}`;
    }
    case 429: {
      const ra = headers.get("retry-after");
      return `Superion S1 rate limit or daily quota reached (429).${ra ? ` Retry after ${ra} s.` : ""} Do not retry in a tight loop.${tail}`;
    }
    case 413:
      return `Superion S1: request body too large (413, max 4 MB). Send a shorter text.${tail}`;
    case 422:
      return `Superion S1 could not process the request (422): usually the text is too long (max 32,768 tokens per question) or a field is invalid. Inputs are never truncated.${tail}`;
    default:
      if (status >= 500) return `Superion S1 service error (${status}). Try again shortly; status: https://punkytigerlabs.com/s1/status.${tail}`;
      return `Superion S1 rejected the request (${status}). Fix the arguments and try again.${tail}`;
  }
}

export class SuperionClient {
  readonly baseURL: string;
  readonly model?: string;
  readonly timeout: number;
  readonly maxRetries: number;
  #apiKey?: string;
  #fetch: typeof fetch;

  constructor(opts: ClientOptions = {}) {
    this.#apiKey = opts.apiKey || process.env.SUPERION_API_KEY || undefined;
    this.baseURL = (opts.baseURL || process.env.SUPERION_BASE_URL || DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.model = opts.model || process.env.SUPERION_MODEL || undefined;
    this.timeout = opts.timeout ?? 120_000;
    this.maxRetries = opts.maxRetries ?? 2;
    this.#fetch = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /** Never expose the key when the client is logged or serialized. */
  toJSON() { return { baseURL: this.baseURL, model: this.model, hasKey: Boolean(this.#apiKey) }; }

  async decide(state: string, questions: Record<string, Question>): Promise<DecisionResponse> {
    if (!this.#apiKey) {
      throw new SuperionError(
        `SUPERION_API_KEY is not set. Add it to the "env" block of this MCP server in your client config. Free key (20 M tokens/day): ${KEY_URL}`,
      );
    }
    const payload: Record<string, unknown> = { state, questions };
    if (this.model) payload.model = this.model;
    const init = {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.#apiKey}`,
        "Content-Type": "application/json",
        Accept: "application/json",
        "User-Agent": `superion-s1-mcp/${VERSION}`,
      },
      body: JSON.stringify(payload),
    };

    for (let attempt = 0; ; attempt++) {
      let res: Response;
      try {
        res = await this.#fetch(`${this.baseURL}/v1/systemone`, { ...init, signal: AbortSignal.timeout(this.timeout) });
      } catch (e) {
        if (attempt < this.maxRetries) { await sleep(500 * 2 ** attempt); continue; }
        const err = e as Error;
        if (err?.name === "TimeoutError") throw new SuperionError(`Superion S1 did not answer within ${this.timeout / 1000} s.`);
        throw new SuperionError(`Could not reach Superion S1 at ${this.baseURL}: ${err?.message ?? String(e)}`);
      }
      const text = await res.text();
      let body: unknown = text;
      try { body = text ? JSON.parse(text) : undefined; } catch { /* keep raw text */ }
      if (res.ok) return body as DecisionResponse;

      if (RETRYABLE.has(res.status) && attempt < this.maxRetries) {
        const raHeader = res.headers.get("retry-after");
        const ra = raHeader === null ? NaN : Number(raHeader);
        const wait = Number.isFinite(ra) && ra >= 0 ? ra * 1000 : 500 * 2 ** attempt;
        if (wait <= MAX_RETRY_WAIT_MS) { await sleep(wait); continue; }
      }
      throw new SuperionError(errorMessage(res.status, body, res.headers), res.status, res.headers.get("x-request-id") ?? undefined);
    }
  }
}
