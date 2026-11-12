"""pip install llama-index-tools-superion llama-index-llms-openai"""
import asyncio

from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.tools.superion import SuperionToolSpec

agent = FunctionAgent(
    tools=SuperionToolSpec().to_tool_list(),
    llm=OpenAI(model="gpt-5-mini"),
    system_prompt="Use the Superion tools to triage support tickets: team, urgency and refund request.",
)


async def main():
    print(await agent.run("Ticket: my card was charged twice for order #4411, fix it today!"))


asyncio.run(main())
