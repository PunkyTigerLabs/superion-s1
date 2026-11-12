"""Superion S1 decision tool for LangChain agents."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Literal, Optional, Type

from langchain_core.callbacks import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_core.utils import secret_from_env
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, SecretStr, model_validator
from superion_s1 import DEFAULT_MODEL, AsyncSuperion, Superion, choice, noul, score
from superion_s1._questions import Question


class SuperionDecisionInput(BaseModel):
    """Input for the Superion S1 decision tool."""

    state: str = Field(description="The text to judge: a message, ticket, document, transcript or proposed action.")
    question: str = Field(description="The question to answer about the text, written for a careful human reviewer.")
    type: Literal["noul", "choice", "score"] = Field(
        default="noul",
        description="noul = yes/no; choice = pick one option; score = rate on an ordered scale (lowest first).")
    options: Optional[List[str]] = Field(
        default=None,
        description="For choice: 2-255 option labels. For score: 2-16 ordered levels, lowest first. Omit for noul.")


def _question(question: str, type: str, options: Optional[List[str]]) -> Question:
    if type == "noul":
        return noul(question)
    if not options:
        raise ValueError(f"options are required for type={type}")
    return choice(question, options) if type == "choice" else score(question, options)


def _format(answer: Any, type: str) -> str:
    if type == "noul":
        return json.dumps({"type": "noul", "p_yes": round(answer.p, 4)})
    if type == "choice":
        return json.dumps({"type": "choice", "best": answer.best,
                           "probabilities": {k: round(v, 4) for k, v in answer.ranked()}})
    return json.dumps({"type": "score", "best": answer.best_label, "expected_level": round(answer.expected, 3),
                       "probabilities": {lvl: round(answer.probabilities[i], 4) for i, lvl in enumerate(answer.levels or [])}})


class SuperionDecisionTool(BaseTool):  # type: ignore[override]
    """Superion S1 calibrated decision tool.

    Answers a yes/no, choice or score question about a text with calibrated probabilities,
    in one API call, without generating text.

    Setup:
        .. code-block:: bash

            pip install -U langchain-superion
            export SUPERION_API_KEY="s1k_..."   # free key: https://punkytigerlabs.com/s1/

    Instantiate:
        .. code-block:: python

            from langchain_superion import SuperionDecisionTool
            tool = SuperionDecisionTool()

    Invoke directly with args:
        .. code-block:: python

            tool.invoke({"state": "Message: I want my money back.",
                         "question": "Does the customer ask for a refund?"})
            # '{"type": "noul", "p_yes": 0.9991}'

    Invoke with a ToolCall:
        .. code-block:: python

            tool.invoke({"args": {"state": "...", "question": "...", "type": "choice",
                                  "options": ["billing", "tech", "sales"]},
                         "id": "1", "name": tool.name, "type": "tool_call"})
    """

    name: str = "superion_decision"
    description: str = (
        "Calibrated judgement about a text. Use it to classify, moderate, triage, score or check whether an "
        "action is safe. Returns probabilities, not prose. type=noul for yes/no, choice for one of several "
        "options, score for an ordered scale.")
    args_schema: Type[BaseModel] = SuperionDecisionInput

    api_key: SecretStr = Field(default_factory=secret_from_env("SUPERION_API_KEY", default=""))
    model: str = DEFAULT_MODEL
    base_url: Optional[str] = None
    timeout: float = 120.0

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _client: Optional[Superion] = PrivateAttr(default=None)
    _aclient: Optional[AsyncSuperion] = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _check_key(self) -> "SuperionDecisionTool":
        if not self.api_key.get_secret_value():
            raise ValueError("Set SUPERION_API_KEY or pass api_key. Free key: https://punkytigerlabs.com/s1/")
        return self

    def _kwargs(self) -> Dict[str, Any]:
        return {"api_key": self.api_key.get_secret_value(), "model": self.model, "base_url": self.base_url,
                "timeout": self.timeout}

    @property
    def client(self) -> Superion:
        if self._client is None:
            self._client = Superion(**self._kwargs())
        return self._client

    @property
    def async_client(self) -> AsyncSuperion:
        if self._aclient is None:
            self._aclient = AsyncSuperion(**self._kwargs())
        return self._aclient

    def _run(self, state: str, question: str, type: str = "noul", options: Optional[List[str]] = None,
             run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        d = self.client.decide(state, {"q": _question(question, type, options)})
        return _format(d["q"], type)

    async def _arun(self, state: str, question: str, type: str = "noul", options: Optional[List[str]] = None,
                    run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> str:
        d = await self.async_client.decide(state, {"q": _question(question, type, options)})
        return _format(d["q"], type)
