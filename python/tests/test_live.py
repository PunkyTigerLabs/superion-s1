"""Live smoke test against the real API. Runs only when SUPERION_API_KEY is set and S1_LIVE=1."""
import os

import pytest

from superion_s1 import AsyncSuperion, Superion, choice, noul, score

pytestmark = [pytest.mark.live, pytest.mark.skipif(
    not (os.environ.get("S1_LIVE") and os.environ.get("SUPERION_API_KEY")), reason="set S1_LIVE=1 and SUPERION_API_KEY")]

STATE = "Message: The laptop arrived broken. I want my money back now, this is unacceptable."


def test_live_decide():
    with Superion() as c:
        d = c.decide(STATE, {
            "refund": noul("Does the customer ask for a refund or a replacement?"),
            "sentiment": choice("Overall sentiment of the message.", {"pos": "positive", "neg": "negative", "neu": "neutral"}),
            "urgency": score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
        })
        assert d["refund"].p > 0.9 and d["sentiment"].best == "neg" and d["urgency"].best == 2
        assert d.usage.input_tokens > 0 and d.usage.output_tokens == 0


async def test_live_async_noul():
    async with AsyncSuperion() as c:
        assert await c.noul(STATE, "Is the customer happy?") < 0.1
