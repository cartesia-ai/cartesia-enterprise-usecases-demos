"""Inbound support triage with Cartesia Line.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

Tool types used below (loopback tools + agent_as_handoff):
  https://docs.cartesia.ai/line/sdk/tools

Setup:
  uv add cartesia-line
  export CARTESIA_API_KEY="your-cartesia-api-key"
  export ANTHROPIC_API_KEY="your-anthropic-api-key"

Run:
  uv run python examples/04_inbound_support_triage/04_inbound_support_triage.py
  cartesia chat 8000
"""

import json
import os
from typing import Annotated

from loguru import logger
from line import AgentEndCall
from line.llm_agent import (
    LlmAgent,
    LlmConfig,
    ToolEnv,
    agent_as_handoff,
    end_call,
    loopback_tool,
)
from line.voice_agent_app import AgentEnv, CallRequest, VoiceAgentApp


# Reasoning model for triage. The "anthropic/" prefix routes the call to
# Anthropic via LiteLLM; without it the SDK defaults to OpenAI.
MODEL = "anthropic/claude-sonnet-4-5"
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # see guide Setup

# Mock stores. Replace with CRM + helpdesk APIs before production.
# Keyed by the digits of the phone number, so any format the caller says matches.
CUSTOMERS = {
    "5550100": {
        "customer_id": "cust_001",
        "name": "Alex Rivera",
        "plan": "Enterprise Support",
        "status": "active",
    }
}

TICKETS: list[dict] = []

# Resolved-customer state for the current call. lookup_customer (triage) writes it;
# get_account_status (a specialist, after handoff) reads it — so the specialist
# doesn't re-interrogate the caller for what triage already resolved.
# Demo-scoped: one call at a time. Production would scope this per call.
CALL_STATE: dict = {}


@loopback_tool
async def lookup_customer(
    ctx: ToolEnv,
    phone_number: Annotated[str, "Caller phone number, any format."],
) -> str:
    # Mock CRM lookup. Match on digits only so formatting doesn't matter.
    logger.info(f"[lookup_customer()] Looking up customer for phone number: {phone_number}")
    digits = "".join(c for c in phone_number if c.isdigit())
    customer = CUSTOMERS.get(digits)
    if customer:
        CALL_STATE["customer"] = customer  # carries across the handoff
    return json.dumps({"found": bool(customer), "customer": customer})


@loopback_tool
async def create_support_ticket(
    ctx: ToolEnv,
    customer_id: Annotated[str, "Customer ID from lookup_customer."],
    intent: Annotated[str, "One of: billing, technical, account, escalation."],
    summary: Annotated[str, "Short issue summary."],
    priority: Annotated[str, "One of: low, normal, high."],
) -> str:
    # Mock ticket creation in the in-memory TICKETS store.
    logger.info(f"[create_support_ticket()] Creating support ticket for customer: {customer_id} with intent: {intent}, summary: {summary}, priority: {priority}")
    ticket = {
        "ticket_id": f"CASE-{len(TICKETS) + 1:04d}",
        "customer_id": customer_id,
        "intent": intent,
        "summary": summary,
        "priority": priority,
        "channel": "voice",
    }
    TICKETS.append(ticket)
    print(json.dumps({"created_ticket": ticket}, indent=2))
    return json.dumps({"created": True, "ticket": ticket})


@loopback_tool
async def get_account_status(ctx: ToolEnv) -> str:
    # Reads the customer triage already resolved (no need to re-ask the caller).
    customer = CALL_STATE.get("customer")
    logger.info(f"[get_account_status()] Account status for: {customer['customer_id'] if customer else None}")
    if not customer:
        return json.dumps({"error": "no_customer_resolved"})
    return json.dumps({"status": customer["status"], "plan": customer["plan"]})


@loopback_tool
async def transfer_to_human(
    ctx: ToolEnv,
    reason: Annotated[str, "Reason for human transfer."],
):
    # For now, Mock human transfer (log it and hang up). A real transfer to a live agent
    # needs a telephony provider — read more:
    #   https://docs.cartesia.ai/line/integrations/calls-api
    # and would call: 
    #   yield AgentTransferCall(target_phone_number="+1...")
    logger.info(f"[transfer_to_human()] Mock human transfer requested: {reason}")
    yield AgentEndCall()


async def get_agent(env: AgentEnv, call_request: CallRequest):
    billing_agent = LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[get_account_status, end_call],
        config=LlmConfig(
            introduction="Hi, this is billing — I can see your case. What can I help with?",
            system_prompt=(
                "You are the Acme billing specialist. Continue the same call. Be brief. "
                "You only handle billing. Do not offer to transfer to other teams."
            ),
        ),
    )

    technical_agent = LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[get_account_status, end_call],
        config=LlmConfig(
            introduction="Hi, this is technical support — I can see your case. What's going on?",
            system_prompt=(
                "You are the Acme technical support specialist. Continue the same call. Be brief. "
                "You only handle technical issues. Do not offer to transfer to other teams."
            ),
        ),
    )

    return LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[
            lookup_customer,
            create_support_ticket,
            # agent_as_handoff is a tool that handsoff control to another defined agent.
            agent_as_handoff(
                billing_agent,
                name="transfer_to_billing",
                description="Transfer billing issues to the billing specialist.",
                handoff_message="Connecting you to billing now.",
            ),
            agent_as_handoff(
                technical_agent,
                name="transfer_to_technical",
                description="Transfer technical issues to the technical specialist.",
                handoff_message="Connecting you to technical support now.",
            ),
            transfer_to_human,
            end_call,
        ],
        config=LlmConfig(
            introduction="Thanks for calling Acme support. What can I help you with today?",
            system_prompt="""
You are the inbound support triage agent for Acme, a SaaS product company.

Flow:
1. Ask for the caller's phone number.
2. Call lookup_customer.
3. If not found, apologize and call transfer_to_human.
4. Classify the issue as billing, technical, account, or escalation.
5. Ask only for the minimum missing detail needed to summarize the issue.
6. Call create_support_ticket exactly once before routing.
7. Route billing issues to transfer_to_billing.
8. Route technical issues to transfer_to_technical.
9. Route escalation, unsafe, unclear, or high-risk issues to transfer_to_human.
10. Never invent account status, ticket IDs, or customer records.
""",
            max_tokens=400,
        ),
    )


app = VoiceAgentApp(get_agent=get_agent)


if __name__ == "__main__":
    app.run()
