# Superion S1 quickstart (Python SDK). pip install superion-s1
# Free key: https://punkytigerlabs.com/s1/  ->  export SUPERION_API_KEY=s1k_...
from superion_s1 import Superion, noul, choice, score

s1 = Superion()
d = s1.decide(
    "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
    {
        "refund": noul("Does the customer ask for a refund or a replacement?"),
        "sentiment": choice("Overall sentiment of the message.", {"pos": "positive", "neg": "negative", "neu": "neutral"}),
        "urgency": score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
    },
)
print(d["refund"].p, d["sentiment"].best, d["urgency"].best_label)   # 0.9997 neg very urgent
