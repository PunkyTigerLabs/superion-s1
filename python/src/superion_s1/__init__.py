"""Python client for Superion S1 — calibrated decisions API by Punky Tiger Labs.

    from superion_s1 import Superion, noul, choice, score

    s1 = Superion()  # reads SUPERION_API_KEY
    d = s1.decide("Message: The laptop arrived broken. I want my money back.", {
        "refund": noul("Does the customer ask for a refund?"),
        "sentiment": choice("Overall sentiment.", {"pos": "positive", "neg": "negative", "neu": "neutral"}),
        "urgency": score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
    })
    d["refund"].p, d["sentiment"].best, d["urgency"].expected
"""
from ._client import DEFAULT_BASE_URL, DEFAULT_MODEL, AsyncSuperion, Superion
from ._errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InsufficientBalanceError,
    InternalServerError,
    RateLimitError,
    RequestTooLargeError,
    ServiceUnavailableError,
    SuperionError,
    UnprocessableError,
)
from ._questions import ChoiceQuestion, NoulQuestion, Question, ScoreQuestion, choice, noul, score
from ._types import Answer, ChoiceAnswer, Decision, NoulAnswer, ScoreAnswer, TokenUsage
from ._version import __version__

__all__ = [
    "Superion", "AsyncSuperion", "DEFAULT_MODEL", "DEFAULT_BASE_URL",
    "noul", "choice", "score", "Question", "NoulQuestion", "ChoiceQuestion", "ScoreQuestion",
    "Decision", "Answer", "NoulAnswer", "ChoiceAnswer", "ScoreAnswer", "TokenUsage",
    "SuperionError", "APIConnectionError", "APITimeoutError", "APIStatusError", "BadRequestError",
    "AuthenticationError", "InsufficientBalanceError", "RequestTooLargeError", "UnprocessableError",
    "RateLimitError", "ServiceUnavailableError", "InternalServerError", "__version__",
]
