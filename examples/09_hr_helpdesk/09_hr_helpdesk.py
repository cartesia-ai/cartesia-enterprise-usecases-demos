"""Internal HR helpdesk with Cartesia Line.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

An internal helpdesk for employees. The voice agent answers common HR questions
— PTO, benefits, expenses, IT access — from a Cartesia knowledge base of policy
docs, and hands sensitive or personal matters to a human in HR. Ink-2 transcribes
the employee, Sonic-3.5 voices the replies. The knowledge base keeps policy
answers grounded in the company's own documents instead of the model guessing.

IMPORTANT: the knowledge base answers ONLY when this agent is DEPLOYED with policy
folders attached. The query is agent-scoped — it authenticates with a session
token the Cartesia platform mints, which local `cartesia chat` does not have. So
in local chat the lookup returns a "deploy to enable" message instead of policy
text. That is expected, not a bug. See the README for knowledge-base setup.

Tool types used below (loopback tools + agent_as_handoff):
  https://docs.cartesia.ai/line/sdk/tools
Knowledge base:
  https://docs.cartesia.ai/line/knowledge-base

Setup:
  uv add cartesia-line
  export CARTESIA_API_KEY="your-cartesia-api-key"
  export ANTHROPIC_API_KEY="your-anthropic-api-key"

Run:
  uv run python examples/09_hr_helpdesk/09_hr_helpdesk.py
  cartesia chat 8000
"""

import os
from typing import Annotated

from loguru import logger
from line.knowledge_base import KnowledgeBaseError
from line.llm_agent import (
    LlmAgent,
    LlmConfig,
    ToolEnv,
    agent_as_handoff,
    end_call,
    loopback_tool,
)
from line.voice_agent_app import AgentEnv, CallRequest, PreCallResult, VoiceAgentApp


# Reasoning model. The "anthropic/" prefix routes the call to Anthropic via
# LiteLLM; without it the SDK defaults to OpenAI.
MODEL = "anthropic/claude-sonnet-4-5"
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # see guide Setup


@loopback_tool
async def lookup_hr_policy(
    ctx: ToolEnv,
    topic: Annotated[str, "The HR topic the employee is asking about, e.g. parental leave, expense limits, VPN access."],
) -> str:
    """Looks up HR policy in the Cartesia knowledge base. Returns the joined text
    of the matching policy passages, or "No matching policy found." when nothing
    matches. When the knowledge base is not reachable (local session), returns a
    short message telling the user the knowledge base is unavailable and to deploy
    the agent with policy docs attached. The agent answers from this string; it
    does not invent policy.
    """
    # The knowledge base is AGENT-SCOPED: ctx.knowledge_base().query() hits the
    # deployed agent's documents, authenticated with a session token the Cartesia
    # platform forwards at call start. Local `cartesia chat` connects straight to
    # this server with no such token, so the query raises KnowledgeBaseError. We
    # catch it and return a clear message so local chat keeps working; once the
    # agent is deployed with policy folders attached, the same call returns real
    # policy text. See the README for knowledge-base setup.
    logger.info(f"[lookup_hr_policy()] Looking up HR policy for topic: {topic}")
    try:
        kb = ctx.knowledge_base()
        results = await kb.query(f"HR policy: {topic}", top_k=3, timeout_s=2.0)
    except KnowledgeBaseError as e:
        logger.info(f"[lookup_hr_policy()] Knowledge base unavailable: {e}")
        return (
            "Knowledge base unavailable in this local session — it answers once the "
            "agent is deployed with policy docs attached (see README)."
        )
    return "\n\n".join(r["content"] for r in results) or "No matching policy found."


async def get_agent(env: AgentEnv, call_request: CallRequest):
    hr_specialist_agent = LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[end_call],
        config=LlmConfig(
            introduction="Hi, this is HR — I can take it from here. What's going on?",
            system_prompt=(
                "You are a human HR specialist. Continue the same call. Be brief and warm. "
                "You handle sensitive and personal matters — conduct or harassment concerns, "
                "pay disputes, medical or personal leave specifics. Listen, take the details, "
                "and explain the next step. Do not quote firm policy or give definitive rulings; "
                "a person in HR follows up. Do not offer to transfer anywhere else."
            ),
            max_tokens=250,
        ),
    )

    return LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[
            lookup_hr_policy,
            # agent_as_handoff is a tool that hands off control to another defined agent.
            agent_as_handoff(
                hr_specialist_agent,
                name="transfer_to_hr_specialist",
                description="Transfer sensitive or personal matters to a human HR specialist.",
                handoff_message="Let me connect you with someone in HR.",
            ),
            end_call,
        ],
        config=LlmConfig(
            introduction="Hi, this is the HR helpdesk. What can I help you with today?",
            system_prompt="""
You are the internal HR helpdesk assistant for employees at the company. Be brief and helpful.

Flow:
1. For general policy questions (PTO, benefits, expenses, IT access), call lookup_hr_policy
   and answer from what it returns. Do not invent policy.
2. If lookup_hr_policy returns nothing or says the knowledge base is unavailable, tell the
   employee the policy isn't available right now and offer to connect them with HR. Do not guess.
3. Hand off with transfer_to_hr_specialist for sensitive or personal matters: harassment or
   conduct complaints, pay or compensation disputes, medical or personal leave specifics, or
   anything that needs a human or isn't covered by general policy.
4. Never claim to be HR staff, and never give a definitive ruling on a sensitive matter.
""",
            max_tokens=400,
        ),
    )


async def pre_call_handler(call_request: CallRequest):
    # Optional hook that runs once before the call connects — here it just picks the
    # TTS voice. (Default voice id below is Cartesia's "Friendly Host".)
    return PreCallResult(config={"tts": {"voice": os.getenv("CARTESIA_VOICE_ID", "910fb75e-1d20-4840-ac63-ac6b26a71bdc")}})


app = VoiceAgentApp(get_agent=get_agent, pre_call_handler=pre_call_handler)


if __name__ == "__main__":
    app.run()
