import { describe, expect, it } from "vitest";
import { Superion, choice, noul, score } from "../src/index";

const live = process.env.S1_LIVE && process.env.SUPERION_API_KEY;

describe.skipIf(!live)("live API", () => {
  it("decides the docs example", async () => {
    const d = await new Superion().decide("Message: The laptop arrived broken. I want my money back now, this is unacceptable.", {
      refund: noul("Does the customer ask for a refund or a replacement?"),
      sentiment: choice("Overall sentiment of the message.", { pos: "positive", neg: "negative", neu: "neutral" }),
      urgency: score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
    });
    expect(d.answers.refund.p).toBeGreaterThan(0.9);
    expect(d.answers.sentiment.best).toBe("neg");
    expect(d.usage.outputTokens).toBe(0);
  });
});
