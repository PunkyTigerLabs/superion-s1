"""Moderate many comments concurrently."""
import asyncio

from superion_s1 import AsyncSuperion, choice

COMMENTS = ["Great article, thanks!", "Buy cheap watches at http://spam.example", "You are an idiot."]


async def main():
    async with AsyncSuperion() as s1:
        answers = await asyncio.gather(*[
            s1.choice(f"Comment: {c}", "Moderation category of the comment.",
                      {"ok": "acceptable", "spam": "spam", "insult": "insult or harassment"})
            for c in COMMENTS])
    for c, a in zip(COMMENTS, answers):
        print(f"{a.best:7} {a.p:.2f}  {c}")


asyncio.run(main())
