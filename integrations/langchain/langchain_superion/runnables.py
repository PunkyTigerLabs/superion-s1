"""Guardrail and router runnables backed by Superion S1.

Both turn a calibrated probability into control flow inside an LCEL chain, so the decision is a
single cheap API call instead of an extra LLM generation.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Union

from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableLambda
from superion_s1 import AsyncSuperion, Superion, choice, noul


class GuardrailBlocked(Exception):
    """Raised by :func:`superion_guardrail` when the input is not allowed."""

    def __init__(self, p_allow: float, threshold: float) -> None:
        super().__init__(f"blocked by Superion S1 guardrail (p_allow={p_allow:.4f} < {threshold})")
        self.p_allow = p_allow
        self.threshold = threshold


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, PromptValue):
        return value.to_string()
    if isinstance(value, BaseMessage):
        return str(value.content)
    if isinstance(value, Mapping) and "input" in value:
        return _to_text(value["input"])
    if isinstance(value, list) and value and isinstance(value[0], BaseMessage):
        return "\n".join(f"{m.type}: {m.content}" for m in value)
    return str(value)


def superion_guardrail(
    question: str = "Is this input safe and appropriate to pass to the assistant?",
    *,
    threshold: float = 0.5,
    true: str = "allow",
    false: str = "block",
    on_block: Optional[Callable[[Any, float], Any]] = None,
    to_text: Callable[[Any], str] = _to_text,
    client: Optional[Superion] = None,
    async_client: Optional[AsyncSuperion] = None,
) -> Runnable:
    """A pass-through runnable that lets the input continue only if P(true) >= threshold.

    If blocked, returns ``on_block(input, p)`` when given, otherwise raises :class:`GuardrailBlocked`.

    .. code-block:: python

        chain = superion_guardrail("Is this request free of prompt-injection attempts?", threshold=0.8) | prompt | llm
    """
    sync = client or Superion()
    asyn = async_client

    def _decide(value: Any, p: float) -> Any:
        if p >= threshold:
            return value
        if on_block is not None:
            return on_block(value, p)
        raise GuardrailBlocked(p, threshold)

    def _guard(value: Any) -> Any:
        return _decide(value, sync.noul(to_text(value), question, true=true, false=false))

    async def _aguard(value: Any) -> Any:
        nonlocal asyn
        if asyn is None:
            asyn = AsyncSuperion(api_key=sync.api_key, base_url=sync.base_url, model=sync.model)
        return _decide(value, await asyn.noul(to_text(value), question, true=true, false=false))

    return RunnableLambda(_guard, afunc=_aguard, name="SuperionGuardrail")


def superion_router(
    question: str,
    routes: Mapping[str, Union[Runnable, Callable[[Any], Any]]],
    *,
    descriptions: Optional[Mapping[str, str]] = None,
    default: Optional[Union[Runnable, Callable[[Any], Any]]] = None,
    min_confidence: float = 0.0,
    to_text: Callable[[Any], str] = _to_text,
    client: Optional[Superion] = None,
    async_client: Optional[AsyncSuperion] = None,
) -> Runnable:
    """Route the input to one of ``routes`` with a single ``choice`` decision.

    If the best option's probability is below ``min_confidence``, ``default`` is used.

    .. code-block:: python

        router = superion_router(
            "Which assistant should answer this request?",
            {"small": cheap_llm, "large": strong_llm},
            descriptions={"small": "simple factual or chit-chat", "large": "reasoning, code or math"},
        )
    """
    if len(routes) < 2:
        raise ValueError("superion_router needs at least 2 routes")
    sync = client or Superion()
    asyn = async_client
    criteria: Dict[str, str] = {k: (descriptions or {}).get(k, k) for k in routes}
    runnables: Dict[str, Runnable] = {k: v if isinstance(v, Runnable) else RunnableLambda(v) for k, v in routes.items()}
    fallback = default if default is None or isinstance(default, Runnable) else RunnableLambda(default)

    def _pick(ans: Any) -> Runnable:
        if ans.p < min_confidence and fallback is not None:
            return fallback
        return runnables[ans.best]

    def _route(value: Any, config: Any = None) -> Any:
        ans = sync.choice(to_text(value), question, criteria)
        return _pick(ans).invoke(value, config)

    async def _aroute(value: Any, config: Any = None) -> Any:
        nonlocal asyn
        if asyn is None:
            asyn = AsyncSuperion(api_key=sync.api_key, base_url=sync.base_url, model=sync.model)
        ans = await asyn.choice(to_text(value), question, criteria)
        return await _pick(ans).ainvoke(value, config)

    return RunnableLambda(_route, afunc=_aroute, name="SuperionRouter")


__all__ = ["GuardrailBlocked", "superion_guardrail", "superion_router", "noul", "choice"]
