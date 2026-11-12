"""Route support tickets with calibrated probabilities. Usage: SUPERION_API_KEY=... python ticket_triage.py"""
from superion_s1 import Superion, choice, noul, score

TICKETS = [
    "My card was charged twice for the same order #4411. Please fix it today.",
    "How do I export my data to CSV?",
    "The app crashes every time I open the camera on Android 15.",
]

with Superion() as s1:
    for text in TICKETS:
        d = s1.decide(f"Ticket: {text}", {
            "team": choice("Which team should handle this ticket?",
                           {"billing": "billing and payments", "tech": "technical bug", "howto": "how-to question"}),
            "urgency": score("How urgent is a reply?", ["low", "normal", "high"]),
            "refund": noul("Does the customer ask for money back?"),
        })
        team = d["team"]
        action = team.best if team.p >= 0.8 else "human-review"   # calibrated: threshold means what it says
        print(f"{action:13} urgency={d['urgency'].best_label:6} refund={d['refund'].p:.2f}  {text[:50]}")
