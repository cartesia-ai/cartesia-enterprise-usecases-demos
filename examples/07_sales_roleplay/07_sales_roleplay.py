"""Sales role-play and coaching with Cartesia Managed Agents.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

A Managed Agent plays a hesitant prospect so a sales rep can rehearse a pitch.
When the rep asks for feedback, it calls the score_call webhook, switches to
coach mode, reads a fixed mock scorecard, and ends the call.

Managed Agents migration:
  https://docs.cartesia.ai/agents/migrate-from-line-sdk
Webhook tools:
  https://docs.cartesia.ai/agents/webhook-tools

Setup:
  export CARTESIA_API_KEY="your-cartesia-api-key"

Run:
  uv run python examples/07_sales_roleplay/07_sales_roleplay.py serve
  uv run python examples/07_sales_roleplay/07_sales_roleplay.py provision \
    --webhook-base-url https://your-public-tool-url.example
"""

import argparse
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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

Never claim score_call analyzed the conversation. It returns a fixed practice scorecard.
"""


def build_scorecard() -> dict:
    """Return the fixed coaching result used by this mock example."""
    return {
        "dimensions": {
            "discovery": {"score": 3, "note": "Asked about the workflow, but missed the budget owner."},
            "objection_handling": {"score": 4, "note": "Stayed calm on the price pushback."},
            "value_articulation": {"score": 2, "note": "Listed features; tie them to a cost or time saved."},
            "next_step": {"score": 3, "note": "Suggested a follow-up, but didn't lock a date."},
        },
        "overall_tip": "Lead with the problem it costs them, then name one concrete next step.",
    }


def build_webhook_tool_payload(webhook_base_url: str) -> dict:
    """Build the Managed Agents webhook definition for the mock scorer."""
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


def build_agent_payload(tool_id: str, model_id: str, voice_id: str) -> dict:
    """Build the Managed Agent that runs the prospect and coach conversation."""
    return {
        "name": "Sales Role-Play and Coaching",
        "config": {
            "instructions": INSTRUCTIONS,
            "initial_message": INITIAL_MESSAGE,
            "model": {"id": model_id, "max_output_tokens": 400},
            "language": {"primary": "en"},
            "audio": {"output": {"voice_id": voice_id}},
            "tools": [{"id": tool_id}],
            "system_tools": {
                "end_call": {
                    "description": "End the call only after the complete scorecard has been spoken.",
                    "pre_tool_speech": "force",
                }
            },
        },
    }


class ScoreCallHandler(BaseHTTPRequestHandler):
    """Serve the fixed scorecard to Cartesia's webhook-tool request."""

    def do_POST(self):
        if self.path != "/score-call":
            self.send_error(404)
            return

        body = json.dumps(build_scorecard()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args):
        print(f"[score_call] {format % args}")


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    """Create the mock scorecard HTTP server without starting it."""
    return ThreadingHTTPServer((host, port), ScoreCallHandler)


def send_api_request(path: str, api_key: str, payload: dict) -> dict:
    """POST JSON to the Managed Agents API and return its decoded response."""
    request = urllib.request.Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "Cartesia-Version": API_VERSION,
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        details = error.read().decode()
        raise RuntimeError(f"Cartesia API returned {error.code}: {details}") from error


def delete_api_resource(path: str, api_key: str) -> None:
    """Delete a Managed Agents API resource created during failed setup."""
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


def provision_agent(webhook_base_url: str, model_id: str, voice_id: str) -> dict:
    """Create the shared score tool and its Managed Agent.

    webhook_base_url must be a public HTTPS origin serving POST /score-call.
    Returns the newly created tool and agent responses. Raises when the API key
    is missing or Cartesia rejects either resource.
    """
    if not webhook_base_url.startswith("https://"):
        raise ValueError("--webhook-base-url must start with https://")

    api_key = os.environ["CARTESIA_API_KEY"]
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
            error.add_note(f"Could not remove orphaned tool {tool['id']}: {cleanup_error}")
        raise
    return {"tool": tool, "agent": agent}


def parse_args() -> argparse.Namespace:
    """Parse the server or provisioning command."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Serve the mock score_call webhook.")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    provision = commands.add_parser("provision", help="Create the tool and Managed Agent.")
    provision.add_argument("--webhook-base-url", required=True)
    provision.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    provision.add_argument(
        "--voice-id",
        default=os.getenv("CARTESIA_VOICE_ID", DEFAULT_VOICE_ID),
    )
    return parser.parse_args()


def main() -> None:
    """Run the local webhook server or provision the hosted Managed Agent."""
    args = parse_args()
    if args.command == "serve":
        server = create_server(args.host, args.port)
        print(f"Mock score_call webhook listening on http://{args.host}:{args.port}/score-call")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return

    result = provision_agent(
        webhook_base_url=args.webhook_base_url,
        model_id=args.model_id,
        voice_id=args.voice_id,
    )
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
