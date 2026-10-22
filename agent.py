"""LaunchPilot AI - hosted agent bootstrap."""

from uagents import Agent

from protocols import launchpilot_protocol

agent = Agent()

agent.include(launchpilot_protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
