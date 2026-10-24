
from uagents import Agent
from protocols import venture_protocol

agent = Agent(
    name="venturelens_ai",
    port=8000,
    mailbox=True,
)

agent.include(venture_protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
