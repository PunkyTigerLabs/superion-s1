"""Sync and async clients for the Superion S1 API."""
from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, Dict, Iterable, Mapping, Optional, Union

import httpx

from ._errors import APIConnectionError, APIStatusError, APITimeoutError, SuperionError, error_for
from ._questions import Question, choice as _choice, noul as _noul, score as _score, validate_question
from ._types import ChoiceAnswer, Decision, NoulAnswer, ScoreAnswer, parse_decision
from ._version import __version__

__all__ = ["Superion", "AsyncSuperion", "DEFAULT_MODEL", "DEFAULT_BASE_URL"]

DEFAULT_BASE_URL = "https://api.punkytigerlabs.com"
DEFAULT_MODEL = "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc"
DEFAULT_TIMEOUT = 120.0  # a large state can wait up to ~70 s in the fair queue
RETRY_STATUSES = {429, 500, 502, 503, 504}


class _Base:
    def __init__(self, api_key: Optional[str], base_url: Optional[str], model: Optional[str],
                 timeout: float, max_retries: int, max_retry_wait: float) -> None:
        api_key = api_key or os.environ.get("SUPERION_API_KEY")
        if not api_key:
            raise SuperionError(
                "No API key. Pass api_key=... or set SUPERION_API_KEY. Free key: https://punkytigerlabs.com/s1/")
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get("SUPERION_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("SUPERION_MODEL") or DEFAULT_MODEL
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_retry_wait = max_retry_wait

    def __repr__(self) -> str:  # never show the key
        return f"{type(self).__name__}(base_url={self.base_url!r}, model={self.model!r})"

    @property
    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "User-Agent": f"superion-s1-python/{__version__}",
                "Accept": "application/json"}

    def _body(self, state: str, questions: Mapping[str, Question], model: Optional[str]) -> Dict[str, Any]:
        if not isinstance(state, str) or not state:
            raise ValueError("state must be a non-empty string")
        if not questions:
            raise ValueError("questions must be a non-empty mapping")
        for qid, q in questions.items():
            validate_question(qid, q)
        return {"model": model or self.model, "state": state, "questions": dict(questions)}

    def _wait(self, attempt: int, error: Optional[APIStatusError]) -> Optional[float]:
        """Seconds to wait before retry ``attempt`` (1-based), or None to give up."""
        if attempt > self.max_retries:
            return None
        ra = error.retry_after if error is not None else None
        if ra is not None:
            return ra if ra <= self.max_retry_wait else None  # e.g. daily quota: don't sleep until midnight
        return min(self.max_retry_wait, 0.5 * 2 ** (attempt - 1)) * (0.75 + random.random() / 2)

    @staticmethod
    def _check(response: httpx.Response) -> Any:
        try:
            body = response.json()
        except ValueError:
            body = response.text
        if response.status_code >= 400:
            raise error_for(response.status_code, body, response.headers)
        return body


class Superion(_Base):
    """Synchronous client.

    >>> from superion_s1 import Superion, noul
    >>> s1 = Superion()                       # reads SUPERION_API_KEY
    >>> s1.noul("Message: I want my money back.", "Does the customer ask for a refund?")
    0.99...
    """

    def __init__(self, api_key: Optional[str] = None, *, base_url: Optional[str] = None, model: Optional[str] = None,
                 timeout: float = DEFAULT_TIMEOUT, max_retries: int = 2, max_retry_wait: float = 60.0,
                 http_client: Optional[httpx.Client] = None) -> None:
        super().__init__(api_key, base_url, model, timeout, max_retries, max_retry_wait)
        self._client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Superion":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, *, json: Any = None, auth: bool = True) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            try:
                r = self._client.request(method, self.base_url + path, json=json,
                                         headers=self._headers if auth else {"User-Agent": self._headers["User-Agent"]},
                                         timeout=self.timeout)
            except httpx.TimeoutException as e:
                wait = self._wait(attempt, None)
                if wait is None:
                    raise APITimeoutError(str(e) or "request timed out") from e
            except httpx.TransportError as e:
                wait = self._wait(attempt, None)
                if wait is None:
                    raise APIConnectionError(str(e) or type(e).__name__) from e
            else:
                if r.status_code not in RETRY_STATUSES:
                    return r
                err = error_for(r.status_code, _safe_json(r), r.headers)
                wait = self._wait(attempt, err)
                if wait is None:
                    return r
            time.sleep(wait)

    # ── decisions ──────────────────────────────────────────────────────────
    def decide(self, state: str, questions: Mapping[str, Question], *, model: Optional[str] = None) -> Decision:
        """Ask any number of typed questions about ``state`` in one call."""
        body = self._body(state, questions, model)
        r = self._request("POST", "/v1/systemone", json=body)
        return parse_decision(self._check(r), body["questions"], r.headers)

    def noul(self, state: str, instructions: str, *, true: str = "yes", false: str = "no",
             model: Optional[str] = None) -> float:
        """Probability that the answer to a yes/no question is ``true``."""
        ans = self.decide(state, {"q": _noul(instructions, true, false)}, model=model)["q"]
        assert isinstance(ans, NoulAnswer)
        return ans.p

    def choice(self, state: str, instructions: str, options: Union[Mapping[str, str], Iterable[str]], *,
               model: Optional[str] = None) -> ChoiceAnswer:
        ans = self.decide(state, {"q": _choice(instructions, options)}, model=model)["q"]
        assert isinstance(ans, ChoiceAnswer)
        return ans

    def score(self, state: str, instructions: str, levels: Iterable[str], *, model: Optional[str] = None) -> ScoreAnswer:
        ans = self.decide(state, {"q": _score(instructions, levels)}, model=model)["q"]
        assert isinstance(ans, ScoreAnswer)
        return ans

    # ── account and service ────────────────────────────────────────────────
    def models(self) -> list:
        """Served models (``GET /v1/models``, public)."""
        return self._check(self._request("GET", "/v1/models", auth=False))["data"]

    def usage(self) -> Dict[str, Any]:
        """Plan, today's counters, limits and (Prepaid) balance, history and purchases."""
        return self._check(self._request("GET", "/v1/usage"))

    def health(self) -> bool:
        return self._check(self._request("GET", "/health", auth=False)).get("status") == "ok"

    def rotate_key(self) -> Dict[str, Any]:
        """Issue a new key; the current one stops working at once. Returns ``{"api_key": ...}``."""
        return self._check(self._request("POST", "/v1/keys/rotate"))

    def revoke_key(self) -> Dict[str, Any]:
        """Permanently disable the current key."""
        return self._check(self._request("POST", "/v1/keys/revoke"))


class AsyncSuperion(_Base):
    """Asynchronous client with the same methods as :class:`Superion` (awaitable)."""

    def __init__(self, api_key: Optional[str] = None, *, base_url: Optional[str] = None, model: Optional[str] = None,
                 timeout: float = DEFAULT_TIMEOUT, max_retries: int = 2, max_retry_wait: float = 60.0,
                 http_client: Optional[httpx.AsyncClient] = None) -> None:
        super().__init__(api_key, base_url, model, timeout, max_retries, max_retry_wait)
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncSuperion":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _request(self, method: str, path: str, *, json: Any = None, auth: bool = True) -> httpx.Response:
        attempt = 0
        while True:
            attempt += 1
            try:
                r = await self._client.request(method, self.base_url + path, json=json,
                                               headers=self._headers if auth else {"User-Agent": self._headers["User-Agent"]},
                                               timeout=self.timeout)
            except httpx.TimeoutException as e:
                wait = self._wait(attempt, None)
                if wait is None:
                    raise APITimeoutError(str(e) or "request timed out") from e
            except httpx.TransportError as e:
                wait = self._wait(attempt, None)
                if wait is None:
                    raise APIConnectionError(str(e) or type(e).__name__) from e
            else:
                if r.status_code not in RETRY_STATUSES:
                    return r
                err = error_for(r.status_code, _safe_json(r), r.headers)
                wait = self._wait(attempt, err)
                if wait is None:
                    return r
            await asyncio.sleep(wait)

    async def decide(self, state: str, questions: Mapping[str, Question], *, model: Optional[str] = None) -> Decision:
        body = self._body(state, questions, model)
        r = await self._request("POST", "/v1/systemone", json=body)
        return parse_decision(self._check(r), body["questions"], r.headers)

    async def noul(self, state: str, instructions: str, *, true: str = "yes", false: str = "no",
                   model: Optional[str] = None) -> float:
        ans = (await self.decide(state, {"q": _noul(instructions, true, false)}, model=model))["q"]
        assert isinstance(ans, NoulAnswer)
        return ans.p

    async def choice(self, state: str, instructions: str, options: Union[Mapping[str, str], Iterable[str]], *,
                     model: Optional[str] = None) -> ChoiceAnswer:
        ans = (await self.decide(state, {"q": _choice(instructions, options)}, model=model))["q"]
        assert isinstance(ans, ChoiceAnswer)
        return ans

    async def score(self, state: str, instructions: str, levels: Iterable[str], *,
                    model: Optional[str] = None) -> ScoreAnswer:
        ans = (await self.decide(state, {"q": _score(instructions, levels)}, model=model))["q"]
        assert isinstance(ans, ScoreAnswer)
        return ans

    async def models(self) -> list:
        return self._check(await self._request("GET", "/v1/models", auth=False))["data"]

    async def usage(self) -> Dict[str, Any]:
        return self._check(await self._request("GET", "/v1/usage"))

    async def health(self) -> bool:
        return self._check(await self._request("GET", "/health", auth=False)).get("status") == "ok"

    async def rotate_key(self) -> Dict[str, Any]:
        return self._check(await self._request("POST", "/v1/keys/rotate"))

    async def revoke_key(self) -> Dict[str, Any]:
        return self._check(await self._request("POST", "/v1/keys/revoke"))


def _safe_json(r: httpx.Response) -> Any:
    try:
        return r.json()
    except ValueError:
        return r.text
