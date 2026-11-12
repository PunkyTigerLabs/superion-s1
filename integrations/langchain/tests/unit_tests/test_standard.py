from typing import Type

from langchain_tests.unit_tests import ToolsUnitTests

from langchain_superion import SuperionDecisionTool


class TestSuperionDecisionToolUnit(ToolsUnitTests):
    @property
    def tool_constructor(self) -> Type[SuperionDecisionTool]:
        return SuperionDecisionTool

    @property
    def tool_constructor_params(self) -> dict:
        return {"api_key": "s1k_fake"}

    @property
    def tool_invoke_params_example(self) -> dict:
        return {"state": "Message: I want my money back.", "question": "Does the customer ask for a refund?",
                "type": "noul"}

    @property
    def init_from_env_params(self):
        return {"SUPERION_API_KEY": "s1k_from_env"}, {}, {"api_key": "s1k_from_env"}
