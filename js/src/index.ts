/**
 * Superion S1 client — calibrated decisions API by Punky Tiger Labs.
 * Server-side only: the API sends no CORS headers, so your key never lives in a web page.
 */

export const VERSION = "0.1.0";
export const DEFAULT_BASE_URL = "https://api.punkytigerlabs.com";
export const DEFAULT_MODEL = "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc";
const RETRY_STATUSES = new Set([429, 500, 502, 503, 504]);

// ── questions ───────────────────────────────────────────────────────────────
export interface NoulQuestion { type: "noul"; instructions: string; criteria: { true: string; false: string } }
export interface ChoiceQuestion { type: "choice"; instructions: string; criteria: Record<string, string> }
export interface ScoreQuestion { type: "score"; instructions: string; criteria: string[] }
export type Question = NoulQuestion | ChoiceQuestion | ScoreQuestion;

/** Yes/no question. The answer is the probability of `true`. */
export function noul(instructions: string, opts: { true?: string; false?: string } = {}): NoulQuestion {
  return { type: "noul", instructions, criteria: { true: opts.true ?? "yes", false: opts.false ?? "no" } };
}

/** Pick one of 2–255 options: a map `id → description` or a list of labels. */
export function choice(instructions: string, options: Record<string, string> | string[]): ChoiceQuestion {
  const criteria = Array.isArray(options) ? Object.fromEntries(options.map((o) => [o, o])) : { ...options };
  const q: ChoiceQuestion = { type: "choice", instructions, criteria };
  validateQuestion("choice", q);
  return q;
}

/** Ordered scale of 2–16 levels, lowest first. */
export function score(instructions: string, levels: string[]): ScoreQuestion {
  const q: ScoreQuestion = { type: "score", instructions, criteria: [...levels] };
  validateQuestion("score", q);
  return q;
}

export function validateQuestion(id: string, q: Question): void {
  const c = q.criteria as unknown;
  if (q.type === "noul") {
    const keys = c && typeof c === "object" ? Object.keys(c).sort().join(",") : "";
    if (keys !== "false,true") throw new TypeError(`question ${id}: noul criteria must be exactly true/false`);
  } else if (q.type === "choice") {
    const n = c && typeof c === "object" && !Array.isArray(c) ? Object.keys(c).length : 0;
    if (n < 2 || n > 255) throw new TypeError(`question ${id}: choice needs 2..255 options`);
  } else if (q.type === "score") {
    if (!Array.isArray(c) || c.length < 2 || c.length > 16) throw new TypeError(`question ${id}: score supports 2..16 levels`);
  } else {
    throw new TypeError(`question ${id}: type must be one of 'choice', 'noul', 'score'`);
  }
  if (typeof q.instructions !== "string" || !q.instructions.trim()) {
    throw new TypeError(`question ${id}: instructions must be a non-empty string`);
  }
}

// ── answers ─────────────────────────────────────────────────────────────────
export interface RawNoulAnswer { type: "noul"; noul: number }
export interface RawChoiceAnswer { type: "choice"; probabilities: Record<string, number> }
export interface RawScoreAnswer { type: "score"; probabilities: Record<string, number> }
export type RawAnswer = RawNoulAnswer | RawChoiceAnswer | RawScoreAnswer;
export interface DecisionResponse {
  model: string;
  usage: { input_tokens: number; output_tokens: number };
  answers: Record<string, RawAnswer>;
}

export class NoulAnswer {
  readonly type = "noul" as const;
  constructor(readonly p: number) {}
  yes(threshold = 0.5): boolean { return this.p >= threshold; }
}

export class ChoiceAnswer {
  readonly type = "choice" as const;
  constructor(readonly probabilities: Record<string, number>) {}
  get best(): string { return this.ranked()[0][0]; }
  get p(): number { return this.ranked()[0][1]; }
  ranked(): [string, number][] { return Object.entries(this.probabilities).sort((a, b) => b[1] - a[1]); }
}

export class ScoreAnswer {
  readonly type = "score" as const;
  /** Probability per level index (0 = lowest). */
  readonly probabilities: number[];
  constructor(probabilities: Record<string, number>, readonly levels?: string[]) {
    const n = Object.keys(probabilities).length;
    this.probabilities = Array.from({ length: n }, (_, i) => probabilities[String(i)] ?? 0);
  }
  get best(): number { return this.probabilities.indexOf(Math.max(...this.probabilities)); }
  get bestLabel(): string | undefined { return this.levels?.[this.best]; }
  get p(): number { return this.probabilities[this.best]; }
  /** Expected level index in [0, n-1]. */
  get expected(): number { return this.probabilities.reduce((s, p, i) => s + i * p, 0); }
  /** Expected level scaled to [0, 1]. */
  get normalized(): number { const n = this.probabilities.length; return n > 1 ? this.expected / (n - 1) : 0; }
}

export type Answer = NoulAnswer | ChoiceAnswer | ScoreAnswer;
type AnswerFor<Q> = Q extends NoulQuestion ? NoulAnswer : Q extends ChoiceQuestion ? ChoiceAnswer : Q extends ScoreQuestion ? ScoreAnswer : Answer;

export interface Decision<Q extends Record<string, Question> = Record<string, Question>> {
  model: string;
  usage: { inputTokens: number; outputTokens: number };
  answers: { [K in keyof Q]: AnswerFor<Q[K]> };
  raw: DecisionResponse;
  /** All `x-ratelimit-*` response headers. */
  rateLimit: Record<string, string>;
  /** Prepaid balance after this request (`X-S1-Balance-USD`), if sent. */
  balanceUsd?: number;
}

function parseAnswer(a: RawAnswer, q?: Question): Answer {
  if (a.type === "noul") return new NoulAnswer(a.noul);
  if (a.type === "choice") return new ChoiceAnswer(a.probabilities);
  if (a.type === "score") return new ScoreAnswer(a.probabilities, q?.type === "score" ? q.criteria : undefined);
  throw new Error(`unknown answer type ${(a as { type: string }).type}`);
}

// ── errors ──────────────────────────────────────────────────────────────────
export class SuperionError extends Error { override name = "SuperionError"; }
export class APIConnectionError extends SuperionError { override name = "APIConnectionError"; }
export class APITimeoutError extends APIConnectionError { override name = "APITimeoutError"; }
export class APIStatusError extends SuperionError {
  override name = "APIStatusError";
  constructor(readonly status: number, readonly error: string, readonly body: unknown, readonly headers: Record<string, string>) {
    super(`${status}: ${error}`);
  }
  get retryAfter(): number | undefined { const v = this.headers["retry-after"]; return v === undefined ? undefined : Number(v); }
}
export class BadRequestError extends APIStatusError { override name = "BadRequestError"; }
export class AuthenticationError extends APIStatusError { override name = "AuthenticationError"; }
export class InsufficientBalanceError extends APIStatusError {
  override name = "InsufficientBalanceError";
  get balanceUsd(): number | undefined { return (this.body as { balance_usd?: number })?.balance_usd; }
}
export class RequestTooLargeError extends APIStatusError { override name = "RequestTooLargeError"; }
export class UnprocessableError extends APIStatusError { override name = "UnprocessableError"; }
export class RateLimitError extends APIStatusError { override name = "RateLimitError"; }
export class ServiceUnavailableError extends APIStatusError { override name = "ServiceUnavailableError"; }
export class InternalServerError extends APIStatusError { override name = "InternalServerError"; }

const ERRORS: Record<number, typeof APIStatusError> = {
  400: BadRequestError, 401: AuthenticationError, 402: InsufficientBalanceError, 413: RequestTooLargeError,
  422: UnprocessableError, 429: RateLimitError, 503: ServiceUnavailableError,
};

function errorFor(status: number, body: unknown, headers: Record<string, string>): APIStatusError {
  const msg = body && typeof body === "object" && "error" in body ? String((body as { error: unknown }).error) : String(body ?? "error");
  const Cls = ERRORS[status] ?? (status >= 500 ? InternalServerError : APIStatusError);
  return new Cls(status, msg, body, headers);
}

// ── client ──────────────────────────────────────────────────────────────────
export interface SuperionOptions {
  /** Defaults to `process.env.SUPERION_API_KEY`. */
  apiKey?: string;
  baseURL?: string;
  model?: string;
  /** Milliseconds. Default 120 000: a large state can wait up to ~70 s in the fair queue. */
  timeout?: number;
  /** Retries on 429, 5xx and network errors, honouring Retry-After. Default 2. */
  maxRetries?: number;
  /** A Retry-After longer than this (ms) is not waited for (e.g. daily quota). Default 60 000. */
  maxRetryWait?: number;
  fetch?: typeof fetch;
}

const env = (k: string): string | undefined =>
  typeof process !== "undefined" && process.env ? process.env[k] : undefined;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export class Superion {
  readonly baseURL: string;
  readonly model: string;
  readonly timeout: number;
  readonly maxRetries: number;
  readonly maxRetryWait: number;
  #apiKey: string;
  #fetch: typeof fetch;

  constructor(opts: SuperionOptions = {}) {
    const key = opts.apiKey ?? env("SUPERION_API_KEY");
    if (!key) throw new SuperionError("No API key. Pass { apiKey } or set SUPERION_API_KEY. Free key: https://punkytigerlabs.com/s1/");
    this.#apiKey = key;
    this.baseURL = (opts.baseURL ?? env("SUPERION_BASE_URL") ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.model = opts.model ?? env("SUPERION_MODEL") ?? DEFAULT_MODEL;
    this.timeout = opts.timeout ?? 120_000;
    this.maxRetries = opts.maxRetries ?? 2;
    this.maxRetryWait = opts.maxRetryWait ?? 60_000;
    this.#fetch = opts.fetch ?? globalThis.fetch.bind(globalThis);
  }

  /** Ask any number of typed questions about `state` in one call. */
  async decide<Q extends Record<string, Question>>(state: string, questions: Q, opts: { model?: string; signal?: AbortSignal } = {}): Promise<Decision<Q>> {
    if (typeof state !== "string" || !state) throw new TypeError("state must be a non-empty string");
    const ids = Object.keys(questions);
    if (!ids.length) throw new TypeError("questions must be a non-empty object");
    for (const id of ids) validateQuestion(id, questions[id]);
    const { body, headers } = await this.#request<DecisionResponse>("POST", "/v1/systemone",
      { model: opts.model ?? this.model, state, questions }, true, opts.signal);
    const answers = Object.fromEntries(Object.entries(body.answers).map(([id, a]) => [id, parseAnswer(a, questions[id])]));
    const bal = headers["x-s1-balance-usd"];
    return {
      model: body.model,
      usage: { inputTokens: body.usage?.input_tokens ?? 0, outputTokens: body.usage?.output_tokens ?? 0 },
      answers: answers as Decision<Q>["answers"],
      raw: body,
      rateLimit: Object.fromEntries(Object.entries(headers).filter(([k]) => k.startsWith("x-ratelimit-"))),
      balanceUsd: bal === undefined ? undefined : Number(bal),
    };
  }

  /** Probability that the answer to a yes/no question is `true`. */
  async noul(state: string, instructions: string, opts: { true?: string; false?: string; model?: string } = {}): Promise<number> {
    return (await this.decide(state, { q: noul(instructions, opts) }, opts)).answers.q.p;
  }

  async choice(state: string, instructions: string, options: Record<string, string> | string[], opts: { model?: string } = {}): Promise<ChoiceAnswer> {
    return (await this.decide(state, { q: choice(instructions, options) }, opts)).answers.q;
  }

  async score(state: string, instructions: string, levels: string[], opts: { model?: string } = {}): Promise<ScoreAnswer> {
    return (await this.decide(state, { q: score(instructions, levels) }, opts)).answers.q;
  }

  /** Served models (public). */
  async models(): Promise<Array<{ id: string; [k: string]: unknown }>> {
    return (await this.#request<{ data: Array<{ id: string }> }>("GET", "/v1/models", undefined, false)).body.data;
  }

  /** Plan, today's counters, limits and (Prepaid) balance, history and purchases. */
  async usage(): Promise<Record<string, unknown>> {
    return (await this.#request<Record<string, unknown>>("GET", "/v1/usage")).body;
  }

  async health(): Promise<boolean> {
    return (await this.#request<{ status: string }>("GET", "/health", undefined, false)).body.status === "ok";
  }

  /** New key; the current one stops working at once. */
  async rotateKey(): Promise<{ api_key: string; key_id: string; [k: string]: unknown }> {
    return (await this.#request<{ api_key: string; key_id: string }>("POST", "/v1/keys/rotate")).body;
  }

  async revokeKey(): Promise<{ key_id: string; revoked: boolean }> {
    return (await this.#request<{ key_id: string; revoked: boolean }>("POST", "/v1/keys/revoke")).body;
  }

  toJSON() { return { baseURL: this.baseURL, model: this.model }; }

  #backoff(attempt: number, err?: APIStatusError): number | undefined {
    if (attempt > this.maxRetries) return undefined;
    const ra = err?.retryAfter;
    if (ra !== undefined && !Number.isNaN(ra)) return ra * 1000 <= this.maxRetryWait ? ra * 1000 : undefined;
    return Math.min(this.maxRetryWait, 500 * 2 ** (attempt - 1)) * (0.75 + Math.random() / 2);
  }

  async #request<T>(method: string, path: string, json?: unknown, auth = true, signal?: AbortSignal): Promise<{ body: T; headers: Record<string, string> }> {
    const headers: Record<string, string> = { Accept: "application/json", "User-Agent": `superion-s1-js/${VERSION}` };
    if (auth) headers.Authorization = `Bearer ${this.#apiKey}`;
    if (json !== undefined) headers["Content-Type"] = "application/json";
    for (let attempt = 1; ; attempt++) {
      let res: Response;
      try {
        const timeout = AbortSignal.timeout(this.timeout);
        res = await this.#fetch(this.baseURL + path, {
          method, headers, body: json === undefined ? undefined : JSON.stringify(json),
          signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
        });
      } catch (e) {
        if (signal?.aborted) throw e;
        const wait = this.#backoff(attempt);
        if (wait === undefined) {
          const err = e as Error;
          if (err?.name === "TimeoutError") throw new APITimeoutError("request timed out");
          throw new APIConnectionError(err?.message ?? String(e));
        }
        await sleep(wait);
        continue;
      }
      const h: Record<string, string> = {};
      res.headers.forEach((v, k) => { h[k.toLowerCase()] = v; });
      const text = await res.text();
      let body: unknown = text;
      try { body = text ? JSON.parse(text) : undefined; } catch { /* keep text */ }
      if (res.ok) return { body: body as T, headers: h };
      const err = errorFor(res.status, body, h);
      if (RETRY_STATUSES.has(res.status)) {
        const wait = this.#backoff(attempt, err);
        if (wait !== undefined) { await sleep(wait); continue; }
      }
      throw err;
    }
  }
}

export default Superion;
