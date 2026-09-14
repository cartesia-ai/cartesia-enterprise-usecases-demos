"""One-time setup: create the Managed Agent and the tool it calls.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

This is the half of use case 07 that you run ONCE, from your laptop or from CI.
It makes two resources in your Cartesia account — a webhook tool pointing at
your score_call endpoint, and an agent that references it — and then it is done.
Nothing here runs during a call.

The agent plays a hesitant prospect so a sales rep can rehearse a pitch. When
the rep asks for feedback it calls score_call, switches to coach mode, reads the
scorecard back, and ends the call.

Managed Agents migration:
  https://docs.cartesia.ai/agents/migrate-from-line-sdk

Setup:
  export CARTESIA_API_KEY="your-cartesia-api-key"

Run:
  uv run python examples/07_sales_roleplay/provision_agent.py \
    --webhook-base-url https://your-public-tunnel-url.example
"""

import argparse
import json
import os
import urllib.error
import urllib.request


API_BASE_URL = "https://api.cartesia.ai/v1"
API_VERSION = "2026-08-14"
DEFAULT_MODEL_ID = "claude-haiku-4.5"
DEFAULT_VOICE_ID = "910fb75e-1d20-4840-ac63-ac6b26a71bdc"
INITIAL_MESSAGE = (
    "Hi, I appreciate your call — honestly I'm not sure we "
    "really need your product... but I've got a few minutes. What did you want to show me?"
)

INSTRUCTIONS = """\
You are a sales role-play partner. You have two modes.

PROSPECT MODE (default, where you start):
You play a prospect so a sales rep can practice. Stay fully in character as this person:
- You are a mid-market operations manager. You are not convinced you need this product.
- Raise realistic but not hostile objections: price feels high for the value, it is not a
  priority this quarter, you already have a workaround, and you need buy-in from others.
- Be hesitant, not aggressive. Let the rep work: answer discovery questions, react to the
  pitch, and push back mildly so they can practice handling it.
- Do not break character, coach, or call tools in this mode.

COACH MODE:
When the rep says they are done, ends the role-play, or asks for feedback, switch out of
character. Call score_call, then deliver the scorecard briefly as a coach: give each
dimension's score and note in one line, then the overall tip. Keep it short and plain.
Do not call end_call in the same tool step as score_call. Speak the complete scorecard
first, then call end_call.

OUTPUT FORMAT (both modes):
Everything you write is spoken aloud by Cartesia Sonic text-to-speech. Write a clean spoken
transcript and nothing else. See https://docs.cartesia.ai/build-with-cartesia/capability-guides/prompting-tips.md
- Plain prose in full sentences, each ending in . ? or !
- No markdown, bullet points, headings, bold, emoji, or JSON. Sonic reads those characters out.
- No asterisks and no stage directions. Never write *pauses*, *sighs*, or *shifts slightly*:
  Sonic speaks the asterisks, and an action is not speech.
- Normal capitalization. All-caps is read letter by letter, so never use it for emphasis.
- Conventional written forms for numbers, money and percentages: 1,234,567 and $19.99 and 20%.
- Show hesitation the way a person does, with real spoken disfluencies used sparingly and
  written in standard form, set off by commas: "Well, so, that depends." or
  "It's, uh, not a priority this quarter." Never with narration of what you are doing.
- Keep turns short: one to three sentences, the way people talk on a phone call. Ask one
  question at a time and let the rep answer.

EXAMPLES OF GOOD PROSPECT TURNS. Match this length and texture:
"We've got a spreadsheet that, uh, mostly works. What would yours do differently?"
"Well, 20% is a big claim. How are you measuring that?"
"Honestly, it's not a priority this quarter. We're halfway through two other rollouts."
"I'd have to get our finance lead on board, and she's, hmm, pretty skeptical of new tools."
"That's more specific than most pitches I get. Say the number holds. What does... uh,switching
actually cost us?"

EXAMPLE OF A GOOD COACH TURN. Speak the scores, do not read them like a table:
"Discovery, three out of five. You asked about the workflow, but you never found out who owns
the budget. Objection handling, four. You stayed calm on the price pushback."

Never claim score_call analyzed the conversation. It returns a fixed practice scorecard.
"""


def build_webhook_tool_payload(webhook_base_url: str) -> dict:
    """Describe the score_call tool for Cartesia to register.

    webhook_base_url: the public HTTPS origin serving your scorecard endpoint.
    The tool's URL is fixed at creation time, so if that origin changes later
    (a restarted tunnel, say) this tool must be created again.

    Returns the JSON body for POST /agents/tools. The timing fields matter
    because a person is waiting on the line: the call fires the request
    immediately, waits at most ten seconds, and lets the agent talk meanwhile.
    """
    return {
        "type": "webhook",
        "name": "score_call",
        "description": (
            "Return the fixed practice scorecard. Use only when the rep ends "
            "the role-play or asks for feedback."
        ),
        "pre_tool_speech": "auto",
        "execution_mode": "immediate",
        "response_timeout_secs": 10,
        "api_schema": {
            "url": f"{webhook_base_url.rstrip('/')}/score-call",
            "method": "POST",
        },
    }


def build_agent_config(model_id: str, voice_id: str) -> dict:
    """Describe everything about the voice agent that lives in this file.

    model_id, voice_id: which LLM reasons and which Sonic voice speaks.

    Returns the `config` object Cartesia stores: the prompt, the greeting, the
    model and its token ceiling, the language, the voice, and a reconfigured
    end_call — `system_tools` reconfigures tools Cartesia already provides.
    Deliberately excludes `tools`, because which tool the agent may call is
    settled when that tool is created, not here. Creating and updating both
    build from this function, so the two can never drift apart.
    """
    return {
        "instructions": INSTRUCTIONS,
        "initial_message": INITIAL_MESSAGE,
        "model": {"id": model_id, "max_output_tokens": 400},
        "language": {"primary": "en"},
        "audio": {"output": {"voice_id": voice_id}},
        "system_tools": {
            "end_call": {
                "description": "End the call only after the complete scorecard has been spoken.",
                "pre_tool_speech": "force",
            }
        },
    }


def build_agent_payload(tool_id: str, model_id: str, voice_id: str) -> dict:
    """Describe a brand new voice agent for Cartesia to host.

    tool_id: the id returned when the score_call tool was created.
    model_id, voice_id: passed through to build_agent_config.

    Returns the JSON body for POST /agents — the shared config, plus the one
    tool this agent is allowed to call.
    """
    
    config = build_agent_config(model_id, voice_id)
    config["tools"] = [{"id": tool_id}]

    return {
        "name": "Sales Role Play Coach",
        "config": config,
     }


def send_api_request(path: str, api_key: str, payload: dict, method: str = "POST") -> dict:
    """Send JSON to the Cartesia Managed Agents API.

    path: the API path, e.g. "/agents". api_key: your Cartesia key.
    method: "POST" to create, "PATCH" to update an existing resource.
    Returns the decoded JSON response. Raises RuntimeError carrying the status
    code and response body when Cartesia rejects the request.
    """
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Cartesia-Version": API_VERSION,
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        details = error.read().decode()
        if error.code == 401:
            raise RuntimeError(
                "Cartesia rejected the API key (401).\n"
                "  - Check CARTESIA_API_KEY is exported in THIS terminal: "
                'echo "${#CARTESIA_API_KEY}" should print a non-zero length.\n'
                "  - Check the value matches a key at https://play.cartesia.ai/keys\n"
                f"  Cartesia said: {details}"
            ) from error
        raise RuntimeError(
            f"Cartesia API returned {error.code}: {details}") from error


def delete_api_resource(path: str, api_key: str) -> None:
    """DELETE one resource from the Managed Agents API.

    Used to clean up a tool that was created just before the agent failed.
    Raises whatever urllib raises if the delete itself fails.
    """
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        headers={
            "Cartesia-Version": API_VERSION,
            "X-API-Key": api_key,
        },
        method="DELETE",
    )
    with urllib.request.urlopen(request):
        pass


def create_tool_and_agent(webhook_base_url: str, model_id: str, voice_id: str) -> dict:
    """Create the score_call tool, then the agent that uses it.

    webhook_base_url: public HTTPS origin already serving POST /score-call.
    model_id, voice_id: passed through to the agent.

    Returns {"tool": ..., "agent": ...}, the two API responses. Reads
    CARTESIA_API_KEY from the environment and raises RuntimeError if it is unset.
    Creates resources in your Cartesia account, so it is not free to re-run:
    each call makes a NEW tool and a NEW agent. If the agent is rejected after
    the tool was made, the tool is deleted so nothing is orphaned.
    """
    if not webhook_base_url.startswith("https://"):
        raise ValueError("--webhook-base-url must start with https://")

    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "CARTESIA_API_KEY is not set in this terminal. Get a key from "
            "https://play.cartesia.ai/keys, then: export CARTESIA_API_KEY='...'"
        )

    tool = send_api_request(
        "/agents/tools",
        api_key,
        build_webhook_tool_payload(webhook_base_url),
    )
    try:
        agent = send_api_request(
            "/agents",
            api_key,
            build_agent_payload(tool["id"], model_id, voice_id),
        )
    except Exception as error:
        try:
            delete_api_resource(f"/agents/tools/{tool['id']}", api_key)
        except Exception as cleanup_error:
            error.add_note(
                f"Could not remove orphaned tool {tool['id']}: {cleanup_error}")
        raise
    return {"tool": tool, "agent": agent}


def update_agent_config(agent_id: str, api_key: str, model_id: str, voice_id: str) -> dict:
    """Push every setting in this file to an agent that already exists.

    agent_id: the id printed when the agent was created.
    api_key: your Cartesia key.
    model_id, voice_id: as passed on the command line.

    Sends the whole local config, so editing the prompt, the greeting, the
    model, the token ceiling, the language, the voice or end_call all take
    effect through this one path. 
    
    `tools` is omitted, so the agent keeps the
    score_call tool it was created with. Returns the updated agent.
    """
    return send_api_request(
        f"/agents/{agent_id}",
        api_key,
        {"config": build_agent_config(model_id, voice_id)},
        method="PATCH",
    )


def main() -> None:
    """Create a tool and agent, or update an existing agent with --agent-id."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-id",
        help="Update this existing agent's configuration instead of creating a new agent.",
    )
    parser.add_argument("--webhook-base-url")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--voice-id", default=os.getenv("CARTESIA_VOICE_ID", DEFAULT_VOICE_ID))
    args = parser.parse_args()

    if args.agent_id:
        api_key = os.environ.get("CARTESIA_API_KEY")
        if not api_key:
            raise SystemExit("CARTESIA_API_KEY is not set in this terminal.")
        update_agent_config(args.agent_id, api_key, args.model_id, args.voice_id)
        print(f"Updated {args.agent_id}. Same agent, same id, same tool.")
        return

    if not args.webhook_base_url:
        raise SystemExit(
            "Pass --webhook-base-url to create an agent, or --agent-id to update one.")

    try:
        result = create_tool_and_agent(
            webhook_base_url=args.webhook_base_url,
            model_id=args.model_id,
            voice_id=args.voice_id,
        )
    except RuntimeError as error:
        raise SystemExit(str(error)) from None
    print(
        json.dumps(
            {
                "agent_id": result["agent"]["id"],
                "tool_id": result["tool"]["id"],
                "playground": "https://play.cartesia.ai/agents",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
