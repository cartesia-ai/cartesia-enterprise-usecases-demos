"""Inbound sales qualification with Cartesia Line.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

A prospect calls the sales line for Northwind Analytics, a B2B SaaS company. The
voice agent qualifies the lead conversationally on BANT — the need, who owns the
decision, whether budget exists, and the timeline — captures the lead, and routes:
a qualified lead is handed to an account executive, an unqualified or not-ready
lead is logged and the call ends politely. Ink-2 transcribes the caller,
Sonic-3.5 voices the replies.

The capture_lead tool is a MOCK — it prints a CRM payload and returns a
confirmation; it does NOT write to a real CRM.

Tool types used below (loopback tools + agent_as_handoff):
  https://docs.cartesia.ai/line/sdk/tools

Setup:
  uv add cartesia-line
  export CARTESIA_API_KEY="your-cartesia-api-key"
  export ANTHROPIC_API_KEY="your-anthropic-api-key"

Run:
  uv run python examples/08_sales_qualification/08_sales_qualification.py
  cartesia chat 8000
"""

import json
import os
from typing import Annotated

from loguru import logger
from line.llm_agent import (
    LlmAgent,
    LlmConfig,
    ToolEnv,
    agent_as_handoff,
    end_call,
    loopback_tool,
)
from line.voice_agent_app import AgentEnv, CallRequest, PreCallResult, VoiceAgentApp


# Reasoning model for qualification. The "anthropic/" prefix routes the call to
# Anthropic via LiteLLM; without it the SDK defaults to OpenAI.
MODEL = "anthropic/claude-sonnet-4-5"
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # see guide Setup


@loopback_tool
async def capture_lead(
    ctx: ToolEnv,
    name: Annotated[str, "Caller's full name."],
    company: Annotated[str, "Caller's company."],
    need: Annotated[str, "The problem or use case they want to solve."],
    authority: Annotated[str, "Whether they decide, and who else is involved."],
    budget: Annotated[str, "Rough budget range, or whether budget exists."],
    timeline: Annotated[str, "When they want to decide or implement."],
    qualified: Annotated[bool, "True if the lead meets the qualification bar."],
) -> str:
    """Records the lead in the CRM. Returns JSON:
      {"recorded": true, "lead": {lead_id, name, company, need, authority,
        budget, timeline, qualified}}.

    The agent reads this to confirm the lead was logged before routing.
    """
    # MOCK CRM write. Replace with your CRM API before production.
    logger.info(f"[capture_lead()] Recording lead for {name} at {company} (qualified={qualified})")
    lead = {
        "lead_id": "LEAD-0001",
        "name": name,
        "company": company,
        "need": need,
        "authority": authority,
        "budget": budget,
        "timeline": timeline,
        "qualified": qualified,
    }
    print(json.dumps({"mock_lead": lead}, indent=2))
    return json.dumps({"recorded": True, "lead": lead})


async def get_agent(env: AgentEnv, call_request: CallRequest):
    # Terminal leaf: the account executive who takes qualified leads. No transfer
    # tools — it only ends the call when done.
    account_executive_agent = LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[end_call],
        config=LlmConfig(
            introduction="Hi, I'm one of the account executives here — I've got the details from your call. Let's talk through next steps.",
            system_prompt=(
                "You are an account executive at Northwind Analytics. Continue the same call with a "
                "qualified lead — you already have what they told the qualification agent, so don't make "
                "them repeat it. Be brief. Discuss their need and next steps. You only take qualified "
                "leads — do not offer to transfer to other teams. When you've agreed on next steps, thank "
                "them and call end_call to wrap up."
            ),
            max_tokens=250,
        ),
    )

    return LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[
            capture_lead,
            agent_as_handoff(
                account_executive_agent,
                name="transfer_to_account_executive",
                description="Transfer a qualified lead to an account executive.",
                handoff_message="Great — connecting you to an account executive now.",
            ),
            end_call,
        ],
        config=LlmConfig(
            max_tokens=400,
            introduction="Thanks for calling Northwind Analytics sales. What can I help you with today?",
            system_prompt="""
You are the inbound sales qualification agent for Northwind Analytics, a B2B SaaS company.

Qualify the caller conversationally on BANT — keep it a short conversation, not an interrogation.
Gather, in your own words and order:
- Name and company.
- Need: the problem or use case they want to solve.
- Authority: whether they make the decision, and who else is involved.
- Budget: a rough range, or whether budget exists at all.
- Timeline: when they want to decide or implement.

Then DECIDE. A lead is QUALIFIED when all of these hold:
- There is a real need our product addresses.
- Budget exists.
- They are the decision maker or can reach the decision maker.
- The timeline is near-term (roughly this quarter or next).

If QUALIFIED: call capture_lead with qualified=true, then call transfer_to_account_executive.
If NOT qualified or not ready: call capture_lead with qualified=false, tell them a rep will
follow up by email, then call end_call.

Call capture_lead exactly once before routing. Never invent lead IDs or claim a real CRM write.
"""        ),
    )


async def pre_call_handler(call_request: CallRequest):
    # Optional hook that runs once before the call connects — here it just picks the
    # TTS voice. (Default voice id below is Cartesia's "Friendly Host".)
    return PreCallResult(
        config={
            "tts": {"voice": os.getenv("CARTESIA_VOICE_ID", "910fb75e-1d20-4840-ac63-ac6b26a71bdc")},
        },
    )


app = VoiceAgentApp(get_agent=get_agent, pre_call_handler=pre_call_handler)


if __name__ == "__main__":
    app.run()
