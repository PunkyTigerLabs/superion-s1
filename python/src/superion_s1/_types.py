"""Typed results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Union

__all__ = ["NoulAnswer", "ChoiceAnswer", "ScoreAnswer", "Answer", "TokenUsage", "Decision", "parse_answer"]


@dataclass(frozen=True)
class NoulAnswer:
    """Yes/no answer. ``p`` is the probability of ``true``."""

    p: float
    type: str = "noul"

    def yes(self, threshold: float = 0.5) -> bool:
        return self.p >= threshold

    def __float__(self) -> float:
        return self.p


@dataclass(frozen=True)
class ChoiceAnswer:
    """Probability per option id (sums to 1)."""

    probabilities: Dict[str, float]
    type: str = "choice"

    @property
    def best(self) -> str:
        """The most likely option id."""
        return max(self.probabilities, key=self.probabilities.__getitem__)

    @property
    def p(self) -> float:
        """Probability of the most likely option."""
        return self.probabilities[self.best]

    def ranked(self) -> List[tuple]:
        return sorted(self.probabilities.items(), key=lambda kv: kv[1], reverse=True)


@dataclass(frozen=True)
class ScoreAnswer:
    """Probability per level index (0 = lowest level)."""

    probabilities: Dict[int, float]
    levels: Optional[List[str]] = None
    type: str = "score"

    @property
    def best(self) -> int:
        """Most likely level index."""
        return max(self.probabilities, key=self.probabilities.__getitem__)

    @property
    def best_label(self) -> Optional[str]:
        return self.levels[self.best] if self.levels else None

    @property
    def p(self) -> float:
        return self.probabilities[self.best]

    @property
    def expected(self) -> float:
        """Expected level index, a continuous score in [0, n-1]."""
        return sum(i * p for i, p in self.probabilities.items())

    @property
    def normalized(self) -> float:
        """Expected level scaled to [0, 1]."""
        n = len(self.probabilities)
        return self.expected / (n - 1) if n > 1 else 0.0


Answer = Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int = 0


@dataclass(frozen=True)
class Decision:
    """Response of ``POST /v1/systemone``. Index it by question id: ``decision["refund"].p``."""

    model: str
    usage: TokenUsage
    answers: Dict[str, Answer]
    raw: Dict[str, Any] = field(repr=False, default_factory=dict)
    headers: Dict[str, str] = field(repr=False, default_factory=dict)

    def __getitem__(self, qid: str) -> Answer:
        return self.answers[qid]

    def __iter__(self):
        return iter(self.answers)

    def __len__(self) -> int:
        return len(self.answers)

    @property
    def balance_usd(self) -> Optional[float]:
        """Prepaid balance after this request (``X-S1-Balance-USD``), if the API sent it."""
        v = self.headers.get("x-s1-balance-usd")
        return float(v) if v is not None else None

    @property
    def rate_limit(self) -> Dict[str, str]:
        """All ``X-RateLimit-*`` headers of the response."""
        return {k: v for k, v in self.headers.items() if k.startswith("x-ratelimit-")}


def parse_answer(data: Mapping[str, Any], question: Optional[Mapping[str, Any]] = None) -> Answer:
    t = data.get("type")
    if t == "noul":
        return NoulAnswer(p=float(data["noul"]))
    if t == "choice":
        return ChoiceAnswer(probabilities={k: float(v) for k, v in data["probabilities"].items()})
    if t == "score":
        levels = list(question["criteria"]) if question and isinstance(question.get("criteria"), list) else None
        probs = {int(k): float(v) for k, v in data["probabilities"].items()}
        return ScoreAnswer(probabilities=dict(sorted(probs.items())), levels=levels)
    raise ValueError(f"unknown answer type: {t!r}")


def parse_decision(body: Mapping[str, Any], questions: Mapping[str, Any], headers: Mapping[str, str]) -> Decision:
    usage = body.get("usage") or {}
    return Decision(
        model=body.get("model", ""),
        usage=TokenUsage(input_tokens=int(usage.get("input_tokens", 0)), output_tokens=int(usage.get("output_tokens", 0))),
        answers={qid: parse_answer(a, questions.get(qid)) for qid, a in (body.get("answers") or {}).items()},
        raw=dict(body),
        headers={k.lower(): v for k, v in headers.items()},
    )
