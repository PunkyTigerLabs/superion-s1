"""LangChain integration for Superion S1 (Punky Tiger Labs) — calibrated decisions API."""
from importlib import metadata

from langchain_superion.runnables import GuardrailBlocked, superion_guardrail, superion_router
from langchain_superion.tools import SuperionDecisionInput, SuperionDecisionTool

try:
    __version__ = metadata.version(__package__)
except metadata.PackageNotFoundError:
    __version__ = ""

__all__ = ["SuperionDecisionTool", "SuperionDecisionInput", "superion_guardrail", "superion_router",
           "GuardrailBlocked", "__version__"]
