// Superion S1 quickstart (server-side fetch, no SDK). Node 18+, Bun, Deno.
const r = await fetch("https://api.punkytigerlabs.com/v1/systemone", {
  method: "POST",
  headers: { Authorization: `Bearer ${process.env.SUPERION_API_KEY}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
    state: "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
    questions: {
      refund: { type: "noul", instructions: "Does the customer ask for a refund or a replacement?", criteria: { true: "yes", false: "no" } },
    },
  }),
});
if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
console.log((await r.json()).answers.refund.noul); // 0.9997
