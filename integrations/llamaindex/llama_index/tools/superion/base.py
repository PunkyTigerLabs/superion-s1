"""Superion S1 tool spec for LlamaIndex agents."""
from __future__ import annotations

import json
import os
from typing import List, Optional

from llama_index.core.tools.tool_spec.base import BaseToolSpec
from superion_s1 import DEFAULT_MODEL, AsyncSuperion, Superion, choice, noul, score


class SuperionToolSpec(BaseToolSpec):
    """Calibrated decisions with Superion S1 (Punky Tiger Labs).

    Three tools: ``decide_yes_no``, ``classify`` and ``score``. Each returns calibrated
    probabilities as JSON from a single API call, without generating text.
    """

    spec_functions = [
        ("decide_yes_no", "adecide_yes_no"),
        ("classify", "aclassify"),
        ("score", "ascore"),
    ]

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL,
                 base_url: Optional[str] = None, timeout: float = 120.0) -> None:
        key = api_key or os.environ.get("SUPERION_API_KEY")
        if not key:
            raise ValueError("Set SUPERION_API_KEY or pass api_key. Free key: https://punkytigerlabs.com/s1/")
        kw = dict(api_key=key, model=model, base_url=base_url, timeout=timeout)
        self.client = Superion(**kw)
        self._akw = kw
        self._aclient: Optional[AsyncSuperion] = None

    @property
    def aclient(self) -> AsyncSuperion:
        if self._aclient is None:
            self._aclient = AsyncSuperion(**self._akw)
        return self._aclient

    # ── yes / no ──
    def decide_yes_no(self, text: str, question: str) -> str:
        """Probability that the answer to a yes/no question about a text is yes.

        Args:
            text (str): The text to judge (message, ticket, document or proposed action).
            question (str): A yes/no question about the text, written for a careful human reviewer.
        """
        return json.dumps({"p_yes": round(self.client.noul(text, question), 4)})

    async def adecide_yes_no(self, text: str, question: str) -> str:
        """Async version of decide_yes_no."""
        return json.dumps({"p_yes": round(await self.aclient.noul(text, question), 4)})

    # ── choice ──
    def classify(self, text: str, question: str, options: List[str]) -> str:
        """Pick the most likely option for a text, with a probability per option.

        Args:
            text (str): The text to classify.
            question (str): What to decide, e.g. "Which team should handle this ticket?".
            options (List[str]): 2 to 255 option labels.
        """
        return _choice_json(self.client.choice(text, question, options))

    async def aclassify(self, text: str, question: str, options: List[str]) -> str:
        """Async version of classify."""
        return _choice_json(await self.aclient.choice(text, question, options))

    # ── score ──
    def score(self, text: str, question: str, levels: List[str]) -> str:
        """Rate a text on an ordered scale, with a probability per level.

        Args:
            text (str): The text to rate.
            question (str): What to rate, e.g. "How urgent is a reply?".
            levels (List[str]): 2 to 16 ordered levels, lowest first.
        """
        return _score_json(self.client.score(text, question, levels))

    async def ascore(self, text: str, question: str, levels: List[str]) -> str:
        """Async version of score."""
        return _score_json(await self.aclient.score(text, question, levels))


def _choice_json(a) -> str:
    return json.dumps({"best": a.best, "probabilities": {k: round(v, 4) for k, v in a.ranked()}})


def _score_json(a) -> str:
    return json.dumps({"best": a.best_label, "expected_level": round(a.expected, 3),
                       "probabilities": {lvl: round(a.probabilities[i], 4) for i, lvl in enumerate(a.levels or [])}})


__all__ = ["SuperionToolSpec", "noul", "choice", "score"]
