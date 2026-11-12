"""Give any tool-calling chat model a calibrated judgement tool.

pip install langchain-superion langchain langchain-openai   # or any chat model provider
"""
from langchain.agents import create_agent
from langchain_superion import SuperionDecisionTool

agent = create_agent(
    model="openai:gpt-5-mini",  # any tool-calling model
    tools=[SuperionDecisionTool()],
    system_prompt="Before answering, use superion_decision to classify the ticket's team and urgency.",
)
print(agent.invoke({"messages": [("user", "Ticket: my card was charged twice for order #4411, fix it today!")]}))
