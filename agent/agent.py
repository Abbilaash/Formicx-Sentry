from strands import Agent
from agent.decision import FormicxKernelGuard
from agent.tools import (
    stop_agent_process,
    modify_agent_policy,
    broadcast_ipc_message,
    execute_host_command,
    revoke_agent_credentials,
    list_running_agents,
)

def create_agent(decider):
    return Agent(
        name="formicx-kernel-agent",
        instructions="You are the Formicx Agent OS Kernel Assistant. You help operators manage, monitor, and safeguard agent fleets.",
        tools=[
            stop_agent_process,
            modify_agent_policy,
            broadcast_ipc_message,
            execute_host_command,
            revoke_agent_credentials,
            list_running_agents,
        ],
        interventions=[FormicxKernelGuard(decider)]
    )