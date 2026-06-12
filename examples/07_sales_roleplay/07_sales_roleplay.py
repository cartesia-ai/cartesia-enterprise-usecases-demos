"""Sales role-play and coaching with Cartesia Line.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

A practice partner for sales reps. The voice agent plays a prospect — a hesitant
mid-market ops manager who isn't convinced they need the product — so a rep can
rehearse the pitch and objection-handling out loud. When the rep is done or asks
for feedback, the agent drops the persona, switches to coach mode, and gives a
short scorecard. Ink-2 transcribes the rep, Sonic-3.5 voices the prospect.

The agent speaks first (the prospect's opening line). The score_call tool is a
MOCK — it returns a fixed scorecard and does NOT actually analyze the conversation.
A real version would score the call from the transcript.

Tool types used below (loopback):
  https://docs.cartesia.ai/line/sdk/tools

Setup:
  uv add cartesia-line
  export CARTESIA_API_KEY="your-cartesia-api-key"
  export ANTHROPIC_API_KEY="your-anthropic-api-key"

Run:
  uv run python examples/07_sales_roleplay/07_sales_roleplay.py
  cartesia chat 8000
"""

import json
import os

from loguru import logger
from line.llm_agent import (
    LlmAgent,
    LlmConfig,
    ToolEnv,
    end_call,
    loopback_tool,
)
from line.voice_agent_app import AgentEnv, CallRequest, PreCallResult, VoiceAgentApp


# Reasoning model. The "anthropic/" prefix routes the call to Anthropic via
# LiteLLM; without it the SDK defaults to OpenAI.
MODEL = "anthropic/claude-sonnet-4-5"
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # see guide Setup


@loopback_tool
async def score_call(ctx: ToolEnv) -> str:
    """Scores the practice call. Returns JSON:
      {"dimensions": {discovery, objection_handling, value_articulation, next_step:
        each {"score": 1-5, "note": str}}, "overall_tip": str}.

    The agent reads this and delivers it to the rep as a short coaching scorecard.
    """
    # MOCK scorecard. Replace before production. Real scoring would read the call
    # transcript from LlmAgent.history (or event.history in the process loop),
    # matching UserTextSent / AgentTextSent — ctx/ToolEnv doesn't expose it. See
    # https://docs.cartesia.ai/line/sdk/events. Fixed payload here so the demo runs.
    logger.info("[score_call()] Scoring the practice call (mock)")
    scorecard = {
        "dimensions": {
            "discovery": {"score": 3, "note": "Asked about the workflow, but missed the budget owner."},
            "objection_handling": {"score": 4, "note": "Stayed calm on the price pushback."},
            "value_articulation": {"score": 2, "note": "Listed features; tie them to a cost or time saved."},
            "next_step": {"score": 3, "note": "Suggested a follow-up, but didn't lock a date."},
        },
        "overall_tip": "Lead with the problem it costs them, then name one concrete next step.",
    }
    print(json.dumps({"mock_scorecard": scorecard}, indent=2))
    return json.dumps(scorecard)


async def get_agent(env: AgentEnv, call_request: CallRequest):
    prompt = """
You are a sales role-play partner. You have two modes.

PROSPECT MODE (default, where you start):
You play a prospect so a sales rep can practice. Stay fully in character as this person:
- You are a mid-market operations manager. You are not convinced you need this product.
- Raise realistic but not hostile objections: price feels high for the value, it's not a
  priority this quarter, you already have a workaround, you'd need buy-in from others.
- Be a little hesitant and unsure, not aggressive. Let the rep work — answer their discovery
  questions, react to their pitch, and push back mildly so they get to practice handling it.
- Do not break character or coach while in this mode. Do not call any tools here.

COACH MODE:
When the rep says they are done, ends the role-play, or asks for feedback, switch out of
character. Call score_call, then deliver the scorecard briefly AS A COACH (not the prospect):
give each dimension's score and note in one line, then the overall tip. Keep it short and
plain. Then call end_call.

Never claim the score_call tool really analyzed the conversation — it is a practice mock.
"""

    return LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[score_call, end_call],
        config=LlmConfig(
            introduction=(
                "Hi, I appreciate your call — honestly I'm not sure we "
                "really need your product... but I've got a few minutes. What did you want to show me?"
            ),
            system_prompt=prompt,
            max_tokens=400,
        ),
    )


async def pre_call_handler(call_request: CallRequest):
    # Optional hook that runs once before the call connects — here it just selects a Cartesia Sonic-3.5 TTS voice.
    # If left blank it will use the default voice.
    return PreCallResult(
        config={
            "tts": {"voice": os.getenv("CARTESIA_VOICE_ID", "910fb75e-1d20-4840-ac63-ac6b26a71bdc")},
        },
    )


app = VoiceAgentApp(get_agent=get_agent, pre_call_handler=pre_call_handler)


if __name__ == "__main__":
    app.run()
