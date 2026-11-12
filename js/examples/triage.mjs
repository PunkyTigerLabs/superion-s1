// node examples/triage.mjs   (needs SUPERION_API_KEY; run `npm run build` first)
import { Superion, choice, noul, score } from "../dist/index.js";

const s1 = new Superion();
const d = await s1.decide("Ticket: My card was charged twice for order #4411. Please fix it today.", {
  team: choice("Which team should handle this ticket?", { billing: "billing and payments", tech: "technical bug", howto: "how-to question" }),
  urgency: score("How urgent is a reply?", ["low", "normal", "high"]),
  refund: noul("Does the customer ask for money back?"),
});
const route = d.answers.team.p >= 0.8 ? d.answers.team.best : "human-review";
console.log({ route, urgency: d.answers.urgency.bestLabel, refund: d.answers.refund.p.toFixed(2), tokens: d.usage.inputTokens });
