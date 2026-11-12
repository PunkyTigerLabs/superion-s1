# Superion S1 quickstart (Python, no SDK). pip install requests
import os, requests

r = requests.post(
    "https://api.punkytigerlabs.com/v1/systemone",
    headers={"Authorization": "Bearer " + os.environ["SUPERION_API_KEY"]},
    json={
        "model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
        "state": "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
        "questions": {
            "refund": {"type": "noul", "instructions": "Does the customer ask for a refund or a replacement?",
                       "criteria": {"true": "yes", "false": "no"}},
        },
    },
    timeout=120,
)
r.raise_for_status()
print(r.json()["answers"]["refund"]["noul"])   # 0.9997
