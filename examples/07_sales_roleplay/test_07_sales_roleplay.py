"""Behavior tests for the UC07 Managed Agent example."""

import importlib.util
import json
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("07_sales_roleplay.py")
SPEC = importlib.util.spec_from_file_location("sales_roleplay_example", MODULE_PATH)
sales_roleplay = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(sales_roleplay)


class ManagedAgentPayloadTests(unittest.TestCase):
    def test_builds_score_call_webhook_tool(self):
        payload = sales_roleplay.build_webhook_tool_payload("https://tools.example.com/")

        self.assertEqual(payload["type"], "webhook")
        self.assertEqual(payload["name"], "score_call")
        self.assertEqual(payload["api_schema"]["url"], "https://tools.example.com/score-call")
        self.assertEqual(payload["api_schema"]["method"], "POST")
        self.assertEqual(payload["execution_mode"], "immediate")

    def test_builds_roleplay_agent_with_tool_and_end_call(self):
        payload = sales_roleplay.build_agent_payload(
            tool_id="agent_tool_123",
            model_id="claude-haiku-4.5",
            voice_id="voice_123",
        )

        config = payload["config"]
        self.assertEqual(config["model"], {"id": "claude-haiku-4.5", "max_output_tokens": 400})
        self.assertEqual(config["audio"]["output"]["voice_id"], "voice_123")
        self.assertEqual(config["language"]["primary"], "en")
        self.assertEqual(config["tools"], [{"id": "agent_tool_123"}])
        self.assertIn("end_call", config["system_tools"])
        self.assertEqual(config["system_tools"]["end_call"]["pre_tool_speech"], "force")
        self.assertIn("after the complete scorecard", config["system_tools"]["end_call"]["description"])
        self.assertIn("PROSPECT MODE", config["instructions"])
        self.assertIn("COACH MODE", config["instructions"])

    def test_removes_tool_when_agent_creation_fails(self):
        with (
            patch.dict("os.environ", {"CARTESIA_API_KEY": "test-key"}),
            patch.object(
                sales_roleplay,
                "send_api_request",
                side_effect=[{"id": "agent_tool_123"}, RuntimeError("agent rejected")],
            ),
            patch.object(sales_roleplay, "delete_api_resource") as delete_resource,
        ):
            with self.assertRaisesRegex(RuntimeError, "agent rejected"):
                sales_roleplay.provision_agent(
                    webhook_base_url="https://tools.example.com",
                    model_id="claude-haiku-4.5",
                    voice_id="voice_123",
                )

        delete_resource.assert_called_once_with("/agents/tools/agent_tool_123", "test-key")


class ScoreCallEndpointTests(unittest.TestCase):
    def test_returns_fixed_scorecard(self):
        server = sales_roleplay.create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/score-call",
                data=b"{}",
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                payload = json.load(response)

            self.assertEqual(payload["dimensions"]["discovery"]["score"], 3)
            self.assertEqual(payload["dimensions"]["objection_handling"]["score"], 4)
            self.assertEqual(payload["dimensions"]["value_articulation"]["score"], 2)
            self.assertEqual(payload["dimensions"]["next_step"]["score"], 3)
            self.assertEqual(
                payload["overall_tip"],
                "Lead with the problem it costs them, then name one concrete next step.",
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
