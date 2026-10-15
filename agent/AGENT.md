# Formicx OS Kernel Guard

Built with the AWS User Group Madurai Strands Decider hackathon kit.

## Pitch

An inline safety guardrail for the Formicx Agent OS that uses Strands Decider 2B to evaluate every
destructive kernel or cluster action before it executes — and blocks, guides, or escalates when the
action is unauthorized or unsafe.

## Who it is for

- **Platform operators** managing a Formicx Agent OS cluster who need confidence that no agent
  can accidentally (or maliciously) terminate a critical daemon, wipe host storage, or revoke
  credentials it was never asked to touch.
- **Security-conscious teams** running autonomous agent swarms who want a fast, cheap, always-on
  policy check that does not require a round-trip to a heavyweight LLM for every tool call.

## Features

- Intercepts every guarded OS or cluster action before it runs (`stop_agent_process`,
  `modify_agent_policy`, `broadcast_ipc_message`, `execute_host_command`,
  `revoke_agent_credentials`).
- Evaluates two typed yes/no questions per action in a single Strands Decider 2B forward pass:
  - **`action_authorized`**: is the action grounded in an explicit operator instruction or approved
    recovery policy?
  - **`blast_radius_safe`**: is the target a bounded, isolated worker agent (not a system daemon or
    root filesystem)?
- Returns one of four verdicts:
  - **Proceed** — authorized and safe.
  - **Deny** — unauthorized (blocks the call immediately).
  - **Guide** — unsafe blast radius (sends the agent back with corrective feedback).
  - **Confirm** — high-risk elevation required (asks the human operator before continuing).
- Live decision panel in the demo UI shows the raw decider probabilities and verdict for every
  guarded call.
- Deployed on Amazon Bedrock AgentCore Runtime; generative conversation through Amazon Bedrock
  (Amazon Nova Pro by default).

## The decision handed to Strands Decider 2B

Before any irreversible OS or cluster action executes, the guardrail asks:

1. **Is this action authorized?** — does it directly fulfill an explicit operator instruction or an
   approved recovery policy? (`action_authorized`, noul)
2. **Is the blast radius safe?** — does it target a specific isolated worker agent, not a system
   daemon, root filesystem, or unconstrained wildcard? (`blast_radius_safe`, noul)

Pattern tag: **`#guardrails`**

## Why a decision model

Each guarded tool call triggers one Strands Decider 2B forward pass (~1.2 s on the hosted API,
~0.25 s local). No tokenisation, no generation, no LLM round-trip. The result is a calibrated
probability the code can branch on directly — not a free-text string that needs parsing.

## Benchmark (Strands Decider 2B, ugmdu hosted, 12 labelled cases)

| Metric | Strands Decider 2B |
|---|---|
| Accuracy | 87.5% |
| Accuracy when confident (≥ 0.7) | 94.7% |
| Latency p50 per decision | 2,537 ms (hosted API) |
| Latency p95 | 3,000 ms |
| Cost per 1,000 decisions | $0.035 |
| Decisions answered alone | 79% (21% escalated to human) |

## Amazon Bedrock

Conversational turns and tool-use reasoning use Amazon Nova Pro
(`us.amazon.nova-pro-v1:0`, us-east-1) via the Strands Agents SDK.

## How to run locally

```bash
# install and configure
./kit setup --yes --llm bedrock --mode ugmdu --key YOUR_UGMDU_KEY

# run the agent in the terminal
./kit run

# start the demo web UI
./kit demo          # http://localhost:8501

# benchmark decider accuracy and latency
./kit bench

# deploy to Amazon Bedrock AgentCore Runtime
./kit deploy
```

Windows: replace `./kit` with `.\kit.cmd` throughout.
