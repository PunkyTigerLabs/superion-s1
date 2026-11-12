// Superion S1 quickstart (Node.js / TypeScript). npm install @punkytigerlabs/superion-s1
// Free key: https://punkytigerlabs.com/s1/  ->  export SUPERION_API_KEY=s1k_...
import { Superion, noul, choice, score } from "@punkytigerlabs/superion-s1";

const s1 = new Superion();
const d = await s1.decide(
  "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
  {
    refund: noul("Does the customer ask for a refund or a replacement?"),
    sentiment: choice("Overall sentiment of the message.", { pos: "positive", neg: "negative", neu: "neutral" }),
    urgency: score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
  },
);
console.log(d.answers.refund.p, d.answers.sentiment.best, d.answers.urgency.bestLabel); // 0.9997 neg very urgent
