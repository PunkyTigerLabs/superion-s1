"""Send each prompt to the cheapest LLM that can handle it."""
from superion_s1 import Superion, score

s1 = Superion()


def route(prompt: str) -> str:
    s = s1.score(f"User prompt: {prompt}", "How hard is this prompt for a language model to answer well?",
                 ["trivial", "easy", "moderate", "hard", "expert-level"])
    return "small-model" if s.expected < 1.5 else "large-model"


print(route("What is the capital of France?"))
print(route("Prove that there are infinitely many primes p such that p+2 is also prime, or explain why it is open."))
