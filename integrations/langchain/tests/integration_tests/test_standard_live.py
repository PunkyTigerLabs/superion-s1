import os
from typing import Type

import pytest
from langchain_tests.integration_tests import ToolsIntegrationTests

from langchain_superion import SuperionDecisionTool

pytestmark = pytest.mark.skipif(not (os.environ.get("S1_LIVE") and os.environ.get("SUPERION_API_KEY")),
                                reason="set S1_LIVE=1 and SUPERION_API_KEY")


class TestSuperionDecisionToolIntegration(ToolsIntegrationTests):
    @property
    def tool_constructor(self) -> Type[SuperionDecisionTool]:
        return SuperionDecisionTool

    @property
    def tool_constructor_params(self) -> dict:
        return {}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"state": "Message: The laptop arrived broken. I want my money back now.",
                "question": "Does the customer ask for a refund?", "type": "noul"}
