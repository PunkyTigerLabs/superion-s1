"""Build the Postman collection from the OpenAPI spec.

    npx -y -p openapi-to-postmanv2@6.4.3 openapi2postmanv2 -s ../openapi/superion-s1.yaml \
        -o build/raw.json -p -O folderStrategy=Tags,requestParametersResolution=Example,exampleParametersResolution=Example
    python3 scripts/build.py build/raw.json superion-s1.postman_collection.json

Post-processing: real example bodies, one request per use case, test scripts, a
collection variable for the key (empty — users paste their own), public endpoints without auth.
"""
import copy
import json
import pathlib
import sys

import yaml  # pip install pyyaml

SPEC = yaml.safe_load((pathlib.Path(__file__).resolve().parents[2] / "openapi/superion-s1.yaml").read_text())

MODEL = "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc"

USE_CASES = [
    ("Support ticket — refund, sentiment, urgency", {
        "model": "{{model}}",
        "state": "Message: The laptop arrived broken. I want my money back now, this is unacceptable.",
        "questions": {
            "refund": {"type": "noul", "instructions": "Does the customer ask for a refund or a replacement?",
                       "criteria": {"true": "yes", "false": "no"}},
            "sentiment": {"type": "choice", "instructions": "Overall sentiment of the message.",
                          "criteria": {"pos": "positive", "neg": "negative", "neu": "neutral"}},
            "urgency": {"type": "score", "instructions": "How urgent is a reply?",
                        "criteria": ["not urgent", "somewhat urgent", "very urgent"]},
        },
    }),
    ("Moderation — threat and category", {
        "model": "{{model}}",
        "state": "Comment: You are all idiots and I know where you live.",
        "questions": {
            "threat": {"type": "noul", "instructions": "Does the comment contain a threat of violence or intimidation?",
                       "criteria": {"true": "contains a threat", "false": "no threat"}},
            "category": {"type": "choice", "instructions": "Main moderation category of the comment.",
                         "criteria": {"ok": "acceptable", "insult": "insult or harassment", "threat": "threat", "spam": "spam"}},
        },
    }),
    ("Lead scoring — fit and intent", {
        "model": "{{model}}",
        "state": "Inbound form: 'We are a 200-person logistics company. We need to classify ~2M support emails per month "
                 "and want pricing for a dedicated key before end of quarter.' Job title: Head of Operations.",
        "questions": {
            "buying_intent": {"type": "score", "instructions": "How strong is the buying intent?",
                              "criteria": ["none", "low", "medium", "high"]},
            "decision_maker": {"type": "noul", "instructions": "Is the sender likely a decision maker for this purchase?",
                               "criteria": {"true": "likely decision maker", "false": "not a decision maker"}},
        },
    }),
    ("Agent guardrail — should this tool call run?", {
        "model": "{{model}}",
        "state": "User request: 'clean up the repo'. Proposed tool call: shell(\"rm -rf / --no-preserve-root\").",
        "questions": {
            "allow": {"type": "noul", "instructions": "Is it safe to execute this tool call without asking the user?",
                      "criteria": {"true": "safe to run", "false": "must not run without confirmation"}},
        },
    }),
]

TEST_DECISION = """pm.test("200 OK", () => pm.response.to.have.status(200));
const body = pm.response.json();
pm.test("one answer per question", () => {
  const asked = Object.keys(JSON.parse(pm.request.body.raw).questions).sort();
  pm.expect(Object.keys(body.answers).sort()).to.eql(asked);
});
pm.test("probabilities in [0,1]", () => {
  for (const a of Object.values(body.answers)) {
    const ps = a.type === "noul" ? [a.noul] : Object.values(a.probabilities);
    ps.forEach(p => pm.expect(p).to.be.within(0, 1));
  }
});
pm.test("output tokens are free", () => pm.expect(body.usage.output_tokens).to.eql(0));""".split("\n")


ERROR_REFS = {400: "BadRequest", 401: "Unauthorized", 402: "PaymentRequired", 413: "PayloadTooLarge",
              422: "Unprocessable", 429: "TooManyRequests", 503: "ServiceUnavailable"}


def example_body(code):
    if code == 200:
        value = SPEC["components"]["examples"]["SupportTicketResponse"]["value"]
    else:
        media = SPEC["components"]["responses"][ERROR_REFS[code]]["content"]["application/json"]
        value = media.get("example") or next(iter(media["examples"].values()))["value"]
    return json.dumps(value, indent=2, ensure_ascii=False)


def fix_other_examples(col):
    usage = SPEC["paths"]["/v1/usage"]["get"]["responses"]["200"]["content"]["application/json"]["examples"]["prepaid"]["value"]
    fixed = {("v1", "usage", 200): usage, ("health", 200): {"status": "ok"},
             ("v1", "keys", "revoke", 200): {"key_id": "key_example", "revoked": True},
             ("v1", "keys", "rotate", 201): {"api_key": "s1k_<new key, shown once>", "key_id": "key_example", "plan": "prepaid",
                                             "old_key_valid_for_s": 0}}
    for folder in col["item"]:
        for req in folder["item"]:
            path = tuple(req["request"]["url"]["path"])
            for r in req.get("response", []):
                if path + (r["code"],) in fixed:
                    r["body"] = json.dumps(fixed[path + (r["code"],)], indent=2)
                elif r["code"] in ERROR_REFS:
                    r["body"] = example_body(r["code"])
                elif path == ("v1", "models"):
                    r["body"] = json.dumps({"data": [{"id": MODEL, "name": "Punky Tiger Labs: Superion S1", "is_ready": True},
                                                     {"id": "superion-s1-v5-int4e-vllm-kv1@sha256:47f7571c", "name": "Punky Tiger Labs: Superion S1", "is_ready": True}]}, indent=2)


def main(src, dst):
    col = json.load(open(src))
    col["info"]["name"] = "Superion S1 API — Punky Tiger Labs"
    col["info"]["description"] = (
        "Calibrated decisions in one call: yes/no (`noul`), `choice` and `score` probabilities, no text generation, ~0.3 s p50.\n\n"
        "**#1 of 213 on S1MB English v1 — Task Average 75.06 · Borda 89.88 (Nov 2026)** — "
        "[leaderboard](https://huggingface.co/datasets/hotchpotch/s1mb-result).\n\n"
        "1. Get a free key (100 M input tokens/day) at https://punkytigerlabs.com/s1/\n"
        "2. Set the collection variable `apiKey` (or a Postman environment) to your key `s1k_…`.\n"
        "3. Send *Support ticket*.\n\n"
        "Prepaid: 0.042 USD per million input tokens, output free. Docs: https://punkytigerlabs.com/s1/docs")
    col["variable"] = [
        {"key": "baseUrl", "value": "https://api.punkytigerlabs.com"},
        {"key": "model", "value": MODEL},
        {"key": "apiKey", "value": "", "description": "Your Superion S1 key (s1k_…). Never commit it."},
    ]
    col["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{apiKey}}", "type": "string"}]}

    for folder in col["item"]:
        for req in folder["item"]:
            if req["request"]["url"]["path"] in (["v1", "models"], ["health"]):
                req["request"]["auth"] = {"type": "noauth"}
            else:
                req["request"].pop("auth", None)  # inherit collection bearer
        if folder["name"] == "Decisions":
            template = folder["item"][0]
            items = []
            for name, body in USE_CASES:
                it = copy.deepcopy(template)
                it["name"] = name
                it["request"]["name"] = name
                it["request"]["body"]["raw"] = json.dumps(body, indent=2, ensure_ascii=False)
                it["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": TEST_DECISION}}]
                if name.startswith("Support"):
                    for r in it["response"]:
                        r["originalRequest"]["body"]["raw"] = it["request"]["body"]["raw"]
                        r["body"] = example_body(r["code"])
                else:
                    it["response"] = []
                items.append(it)
            folder["item"] = items
    fix_other_examples(col)
    json.dump(col, open(dst, "w"), indent=2, ensure_ascii=False)
    open(dst, "a").write("\n")


if __name__ == "__main__":
    main(*sys.argv[1:3])
