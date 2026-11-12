import json
import pathlib
import re

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
COL = json.loads((ROOT / "superion-s1.postman_collection.json").read_text())
SCHEMA = json.loads((ROOT / "tests" / "collection-v2.1.0.schema.json").read_text())


def requests():
    for folder in COL["item"]:
        yield from folder["item"]


def test_valid_postman_v21():
    jsonschema.Draft4Validator(SCHEMA).validate(COL)


def test_no_key_embedded():
    raw = json.dumps(COL)
    assert not re.search(r"s1k_[A-Za-z0-9]{8,}", raw)
    assert {"key": "apiKey", "value": "", "description": "Your Superion S1 key (s1k_…). Never commit it."} in COL["variable"]


def test_decision_bodies_are_real_requests():
    decisions = [r for r in requests() if r["request"]["url"]["path"] == ["v1", "systemone"]]
    assert len(decisions) == 4
    for r in decisions:
        body = json.loads(r["request"]["body"]["raw"])
        assert body["model"] == "{{model}}" and body["state"] and body["questions"]
        assert r["event"][0]["listen"] == "test"


def test_public_endpoints_without_auth():
    for r in requests():
        if r["request"]["url"]["path"] in (["v1", "models"], ["health"]):
            assert r["request"]["auth"] == {"type": "noauth"}
