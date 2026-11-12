"""Question builders: ``noul()``, ``choice()``, ``score()``."""
from __future__ import annotations

from typing import Dict, Iterable, List, Literal, Mapping, TypedDict, Union

__all__ = ["NoulQuestion", "ChoiceQuestion", "ScoreQuestion", "Question", "noul", "choice", "score", "validate_question"]


class NoulQuestion(TypedDict):
    type: Literal["noul"]
    instructions: str
    criteria: Dict[str, str]


class ChoiceQuestion(TypedDict):
    type: Literal["choice"]
    instructions: str
    criteria: Dict[str, str]


class ScoreQuestion(TypedDict):
    type: Literal["score"]
    instructions: str
    criteria: List[str]


Question = Union[NoulQuestion, ChoiceQuestion, ScoreQuestion]


def noul(instructions: str, true: str = "yes", false: str = "no") -> NoulQuestion:
    """A yes/no question. The answer is the probability of ``true``."""
    return {"type": "noul", "instructions": instructions, "criteria": {"true": true, "false": false}}


def choice(instructions: str, options: Union[Mapping[str, str], Iterable[str]]) -> ChoiceQuestion:
    """Pick one of 2–255 options.

    ``options`` is a mapping ``id → description`` or a list of labels (each label is its own id).
    """
    criteria = dict(options) if isinstance(options, Mapping) else {o: o for o in options}
    q: ChoiceQuestion = {"type": "choice", "instructions": instructions, "criteria": criteria}
    validate_question("choice", q)
    return q


def score(instructions: str, levels: Iterable[str]) -> ScoreQuestion:
    """An ordered scale of 2–16 levels, lowest first."""
    q: ScoreQuestion = {"type": "score", "instructions": instructions, "criteria": list(levels)}
    validate_question("score", q)
    return q


def validate_question(qid: str, q: Mapping) -> None:
    """Cheap client-side checks that mirror the API's 400/422 rules (saves a round trip)."""
    t = q.get("type")
    c = q.get("criteria")
    if t == "noul":
        if not isinstance(c, Mapping) or set(c) != {"true", "false"}:
            raise ValueError(f"question {qid}: noul criteria must be exactly true/false")
    elif t == "choice":
        if not isinstance(c, Mapping) or not 2 <= len(c) <= 255:
            raise ValueError(f"question {qid}: choice needs 2..255 options")
    elif t == "score":
        if not isinstance(c, list) or not 2 <= len(c) <= 16:
            raise ValueError(f"question {qid}: score supports 2..16 levels")
    else:
        raise ValueError(f"question {qid}: type must be one of 'choice', 'noul', 'score'")
    if not isinstance(q.get("instructions"), str) or not q["instructions"].strip():
        raise ValueError(f"question {qid}: instructions must be a non-empty string")
