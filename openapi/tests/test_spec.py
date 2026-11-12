"""Validate the spec and check real API responses against its schemas.

Offline by default. Set SUPERION_API_KEY to also run one live request.
"""
import json
import os
import pathlib
import urllib.request

import jsonschema
import pytest
import yaml
from openapi_spec_validator import validate

SPEC_PATH = pathlib.Path(__file__).resolve().parents[1] / "superion-s1.yaml"
SPEC = yaml.safe_load(SPEC_PATH.read_text())
BASE = "https://api.punkytigerlabs.com"


def validator(name):
    schema = {"$ref": f"#/components/schemas/{name}", "components": SPEC["components"]}
    return jsonschema.Draft202012Validator(schema)


def test_spec_is_valid_openapi_31():
    validate(SPEC)
    assert SPEC["openapi"].startswith("3.1")


@pytest.mark.parametrize("name", ["SupportTicketRequest", "ModerationRequest"])
def test_request_examples_match_schema(name):
    validator("DecisionRequest").validate(SPEC["components"]["examples"][name]["value"])


def test_response_example_matches_schema():
    validator("DecisionResponse").validate(SPEC["components"]["examples"]["SupportTicketResponse"]["value"])


# Real response to the support-ticket example, captured 12 Nov 2026 (v6), unrounded.
REAL_RESPONSE = {
    "model": "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc",
    "usage": {"input_tokens": 135, "output_tokens": 0},
    "answers": {
        "refund": {"type": "noul", "noul": 0.9997470683161428},
        "sentiment": {"type": "choice", "probabilities": {"pos": 0.0002855798545093104, "neg": 0.9942880386883389, "neu": 0.005426381457151809}},
        "urgency": {"type": "score", "probabilities": {"0": 1.2019009452913502e-12, "1": 0.19215297234497805, "2": 0.8078470276538201}},
    },
}


def test_real_response_matches_schema():
    validator("DecisionResponse").validate(REAL_RESPONSE)


@pytest.mark.parametrize("bad", [
    {"model": "m", "state": "x", "questions": {}},
    {"model": "m", "state": "x", "questions": {"s": {"type": "score", "instructions": "?", "criteria": [str(i) for i in range(17)]}}},
    {"model": "m", "state": "x", "questions": {"c": {"type": "choice", "instructions": "?", "criteria": {"a": "A"}}}},
    {"model": "m", "state": "x", "questions": {"c": {"type": "noul", "instructions": "?", "criteria": {"true": "y"}}}},
    {"model": "m", "state": "x", "questions": {"c": {"type": "bogus", "instructions": "?"}}},
])
def test_invalid_requests_are_rejected_by_schema(bad):
    with pytest.raises(jsonschema.ValidationError):
        validator("DecisionRequest").validate(bad)


def _get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.load(r)


@pytest.mark.skipif(not os.environ.get("S1_LIVE"), reason="set S1_LIVE=1 for public live checks")
def test_live_models_and_health():
    validator("ModelList").validate(_get("/v1/models"))
    assert _get("/health") == {"status": "ok"}


@pytest.mark.skipif(not os.environ.get("SUPERION_API_KEY"), reason="needs SUPERION_API_KEY")
def test_live_decision_matches_schema():
    body = json.dumps(SPEC["components"]["examples"]["SupportTicketRequest"]["value"]).encode()
    req = urllib.request.Request(BASE + "/v1/systemone", data=body, method="POST", headers={
        "Authorization": "Bearer " + os.environ["SUPERION_API_KEY"], "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        validator("DecisionResponse").validate(json.load(r))


def test_marketplace_spec_hides_account_endpoints():
    m = yaml.safe_load((SPEC_PATH.parent / "superion-s1.marketplace.yaml").read_text())
    validate(m)
    assert set(m["paths"]) == {"/v1/systemone", "/v1/models", "/health"}
    assert m["paths"]["/v1/systemone"] == SPEC["paths"]["/v1/systemone"]
