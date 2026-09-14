"""Your backend: the HTTP endpoint the Managed Agent calls during a live call.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

WHY THIS EXISTS. The agent could invent feedback on its own — models are happy
to tell a rep how they did. You don't want that. Improvised praise varies call
to call, can't be compared between reps, and is based only on what the model
happened to notice. A tool call moves the judgement out of the model and into
your system, so every rep is measured against the same rubric, the result can be
stored and tracked over time, and the score can use things the model cannot see:
CRM outcomes, your sales team's agreed criteria, how this rep did last month.
That is what the tool adds to the agent. Grounding, not plumbing.

This example ships a mock: build_scorecard() returns the same four dimensions
every time. It marks the seam where your real scoring goes. Because the result
is spoken and then gone, a real implementation would write its scores somewhere
before returning them; the log here stands in for that.

Leave this running for as long as the agent is in use.

Webhook tools:
  https://docs.cartesia.ai/agents/webhook-tools

Run:
  uv run python examples/07_sales_roleplay/score_call_server.py
"""

import argparse
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def build_scorecard() -> dict:
    """Return the coaching result this example sends back to the agent.

    The same scorecard every time — this is a mock, so a demo runs without a
    scoring pipeline behind it. Returns four rated dimensions (discovery,
    objection handling, value articulation, next step), each with a 1-5 score
    and a short note, plus one overall tip. Replace this function to score a
    real call from its transcript; nothing else has to change.
    """
    return {
        "dimensions": {
            "discovery": {"score": 3, "note": "Asked about the workflow, but missed the budget owner."},
            "objection_handling": {"score": 4, "note": "Stayed calm on the price pushback."},
            "value_articulation": {"score": 2, "note": "Listed features; tie them to a cost or time saved."},
            "next_step": {"score": 3, "note": "Suggested a follow-up, but didn't lock a date."},
        },
        "overall_tip": "Lead with the problem it costs them, then name one concrete next step.",
    }


class ServerHandler(BaseHTTPRequestHandler):
    """Answers the one request Cartesia makes: POST /score-call.

    Anything else gets a 404. Each request is logged to stdout, which is the
    simplest proof that a live voice call reached this machine.
    """

    def do_POST(self):
        if self.path != "/score-call":
            self.send_error(404)
            return

        request_body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        scorecard = build_scorecard()
        self.log_exchange(request_body, scorecard)
        body = json.dumps(scorecard).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_exchange(self, request_body: bytes, scorecard: dict) -> None:
        """Print what came in and what went back, so a live call is visible.

        request_body: the raw bytes posted. This mock ignores them, but printing
            them shows what Cartesia actually sends.
        scorecard: the response about to be written.

        Prints one block per call: UTC timestamp, caller, request body, scores.
        """
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        scores = ", ".join(f"{name} {value['score']}" for name, value in scorecard["dimensions"].items())
        incoming = request_body.decode(errors="replace").strip() or "(empty body)"
        print(
            f"[score_call] {stamp} from {self.client_address[0]}\n"
            f"  in : {incoming[:500]}\n"
            f"  out: 200, {scores}",
            flush=True,
        )

    def log_message(self, format: str, *args):
        print(f"[score_call] {format % args}", flush=True)


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    """Build the scorecard server, bound but not yet serving.

    host, port: where to listen. Defaults bind to localhost only, because a
    tunnel is what makes this reachable from the internet, not a public bind.
    Returns the server; the caller starts it. Tests use port 0 to get a free
    port from the OS.
    """
    return ThreadingHTTPServer((host, port), ServerHandler)


def main() -> None:
    """Serve the scorecard endpoint until interrupted."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    print(f"score_call endpoint listening on http://{args.host}:{args.port}/score-call", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
