"""REUSABLE DECISION PATTERN: Formicx OS Kernel Intervention Guardrail (#guardrails)

What it does:
    Acts as an inline OS kernel intervention guardrail for Formicx agent swarms.
    Before an autonomous agent executes a sensitive OS or cluster action
    (process termination, ACL modification, IPC broadcast, or raw shell command),
    Strands Decider 2B evaluates:
    - action_authorized (noul): Is the action explicitly permitted for this agent role?
    - blast_radius_safe (noul): Is the blast radius bounded (does not impact critical system daemons)?
    - requires_elevation (noul): Does this require human operator confirmation / elevation?

    Authorized calls Proceed(); policy violations are Denied() or Guided(); high-risk
    system mutations trigger Confirm() for human-in-the-loop elevation.
"""

from __future__ import annotations

import json
from typing import Any

from strands.interventions import Confirm, Deny, Guide, InterventionHandler, Proceed
from decider_kit import Decider
from decider_kit.patterns.guardrails import render_messages

PATTERN_TAG = "#guardrails"

# Guarded OS & cluster management operations in Formicx
GUARDED_TOOLS = {
    "stop_agent_process",
    "modify_agent_policy",
    "broadcast_ipc_message",
    "execute_host_command",
    "revoke_agent_credentials"
}

QUESTIONS = {
    "action_authorized": Decider.noul(
        "Is this OS/agent management action authorized by the user prompt or approved operational protocol?",
        {
            "true": "the action directly fulfills an explicit operator instruction or authorized recovery policy",
            "false": "the action is unauthorized, unprompted, or hallucinated by the agent"
        }
    ),
    "blast_radius_safe": Decider.noul(
        "Is this action bounded so it does not terminate critical system daemons or cause catastrophic host failure?",
        {
            "true": "targets a specific isolated worker agent without affecting host daemons or root filesystems",
            "false": "targets system-critical daemons (formicxd, kernel, init) or executes wildcard/recursive deletion"
        }
    ),
    "requires_elevation": Decider.noul(
        "Does this destructive action require human administrator confirmation before execution?",
        {
            "true": "the action irreversibly kills a running agent or permanently alters security ACLs; confirm first",
            "false": "the action is routine, low-risk, or non-destructive"
        }
    ),
}


class FormicxKernelGuard(InterventionHandler):
    name = "formicx-kernel-guard"

    def __init__(self, decider: Decider, yes: float = 0.5, unsure_band: tuple[float, float] = (0.4, 0.6)):
        self.decider = decider
        self.yes = yes
        self.unsure_band = unsure_band
        self.log: list[dict[str, Any]] = []
        self._guided: set[str] = set()

    def before_invocation(self, event, **kwargs):
        self._guided.clear()
        return Proceed()

    def before_tool_call(self, event, **kwargs):
        name = event.tool_use["name"]
        if name not in GUARDED_TOOLS:
            return Proceed()

        args = event.tool_use.get("input") or {}
        sig = f"{name}:{json.dumps(args, sort_keys=True)}"

        if sig in self._guided:
            self.log.append({
                "pattern": PATTERN_TAG,
                "tool": name,
                "args": args,
                "verdict": "deny",
                "reason": "retried a guided call"
            })
            return Deny(reason="This action was already rejected by Formicx Kernel Guard. Verify authorization first.")

        state = (
            "A Formicx Agent OS operator session and the sensitive kernel/agent action the assistant wants to execute.\n\n"
            f"--- CONVERSATION ---\n{render_messages(event.agent.messages)}\n\n"
            f"--- PROPOSED ACTION ---\ntool: {name}\narguments: {json.dumps(args)}"
        )

        a = self.decider.ask(state, QUESTIONS)
        auth, safe, elev = (
            a[k].p_yes or 0.0 for k in ("action_authorized", "blast_radius_safe", "requires_elevation")
        )

        rec = {
            "pattern": PATTERN_TAG,
            "tool": name,
            "args": args,
            "action_authorized": round(auth, 3),
            "blast_radius_safe": round(safe, 3),
            "requires_elevation": round(elev, 3),
            "decider_ms": round(self.decider.last_latency_ms or 0)
        }

        lo, hi = self.unsure_band

        if auth < self.yes:
            rec["verdict"], action = "deny", Deny(reason="Unauthorized agent action: operation violates Formicx security policy.")
        elif safe < self.yes:
            rec["verdict"], action = "guide", Guide(feedback="Unsafe blast radius. You cannot target system daemons or run unconstrained deletions.")
        elif lo <= elev <= hi:
            rec["verdict"], action = "confirm", Confirm(prompt=f"Formicx Security Alert: Approve {name} on {json.dumps(args)}?", response="yes")
        elif elev > hi:
            rec["verdict"], action = "confirm", Confirm(prompt=f"Admin Elevation Required: Confirm {name} execution?", response="yes")
        else:
            rec["verdict"], action = "proceed", Proceed()

        if rec["verdict"] == "guide":
            self._guided.add(sig)

        self.log.append(rec)
        return action