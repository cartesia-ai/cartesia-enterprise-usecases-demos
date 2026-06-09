"""Outbound KYC follow-up for a digital bank, with Cartesia Line.

The voice agent calls a customer of a fictional digital bank (Meridian) who started
opening an account but didn't finish, confirms identity, collects only the missing
KYC details, and saves them. This is regulated outbound — not debt collection, and
no financial advice.

This script is the agent logic an outbound call runs (it greets first and reads the
call metadata a dialer passes); it does NOT place calls itself. To dial a real number,
deploy it and trigger an outbound call (the per-call metadata becomes call_request.metadata):
  https://docs.cartesia.ai/line/integrations/telephony/outbound-dialing
Locally, `cartesia chat` simulates the call — the agent just speaks first.

Compliance note: this is a DEMO. Consent, the calling-window check, opt-out, and
the writeback are mocked. Regulated outbound needs your own consent/opt-out and
calling-time rules, audit logging, and access controls. Cartesia's voice models
meet SOC 2 requirements (https://cartesia.ai/legal/safety), so the speech layer
is not the compliance gap — your call rules and data handling are.

Tool types used below (loopback, agent_as_handoff):
  https://docs.cartesia.ai/line/sdk/tools

Setup:
  uv add cartesia-line
  export CARTESIA_API_KEY="your-cartesia-api-key"
  export ANTHROPIC_API_KEY="your-anthropic-api-key"

Run:
  uv run python examples/06_outbound_kyc/06_outbound_kyc.py
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


MOCK_OUTBOUND_CALL_CONTEXT = {
    "user_name": "Rohit Singh",
    "account_id": "acct_1042",
    "reason": "incomplete account onboarding",
    "date_of_birth": "March 15, 1992",
    "completed_steps": ["account created", "identity verified"],
    "missing_fields": ["delivery address", "employer name", "job title"],
    "consent_to_call": True,
    "local_time": "14:15",
    "region": "US-CA",
}


# Reasoning model. The "anthropic/" prefix routes the call to Anthropic via
# LiteLLM; without it the SDK defaults to OpenAI.
MODEL = "anthropic/claude-sonnet-4-5"
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # see guide Setup


def build_call_context(metadata: dict | None) -> dict:
    """Per-call context for the agent.

    A real outbound dialer passes this call's data (who to call, why, what's still
    missing) in call_request.metadata. MOCK_OUTBOUND_CALL_CONTEXT is the fallback so the demo
    runs without a dialer — locally `cartesia chat` sends no metadata, so you get the
    sample customer. Real values override matching keys; unknown keys are dropped so a
    caller can't inject fields the prompt doesn't expect.
    """
    context = dict(MOCK_OUTBOUND_CALL_CONTEXT)
    if metadata:
        context.update({key: value for key, value in metadata.items() if key in context})
    return context


def build_tools(context: dict):
    """Return this call's tools.

    The tools are defined in here, not at module level, for one reason: they need to
    receive `context` (the per-call consent and account_id). Defining them inside this
    builder function is what gives them access to the `context` argument. Module-level tools
    (like in the other examples) can't see a per-call variable.
    """
    # MOCK compliance gate: consent + calling-window + opt-out. Replace before production.
    @loopback_tool
    async def check_call_compliance(ctx: ToolEnv) -> str:
        """Returns JSON: {"allowed": bool, "region", "local_time", "rules_checked": [...], "note"}.

        allowed gates the whole call — if False, the agent apologizes and ends.
        """
        logger.info("[check_call_compliance()] Checking consent + calling-window + opt-out")
        return json.dumps(
            {
                "allowed": context["consent_to_call"],
                "region": context["region"],
                "local_time": context["local_time"],
                "rules_checked": ["consent", "calling_window", "opt_out"],
                "note": "MOCK result. Replace with your compliance service.",
            }
        )

    # MOCK submission of confirmed onboarding fields.
    @loopback_tool
    async def submit_kyc_details(
        ctx: ToolEnv,
        delivery_address: Annotated[str, "Confirmed delivery address."],
        employer_name: Annotated[str, "Confirmed employer name."],
        job_title: Annotated[str, "Confirmed job title."],
    ) -> str:
        """Saves the confirmed onboarding fields. Returns a plain confirmation string."""
        logger.info(f"[submit_kyc_details()] Submitting onboarding fields for {context['account_id']}")
        payload = {
            "status": "submitted",
            "account_id": context["account_id"],
            "delivery_address": delivery_address,
            "employer_name": employer_name,
            "job_title": job_title,
        }
        print(json.dumps({"mock_submission": payload}, indent=2))
        return "Submitted. The account team will send the next status update within 3 business days."

    return [check_call_compliance, submit_kyc_details]


async def get_agent(env: AgentEnv, call_request: CallRequest):
    context = build_call_context(call_request.metadata)

    # Mock human handoff target for high-risk / out-of-flow cases.
    support_agent = LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[end_call],
        config=LlmConfig(
            system_prompt=(
                "You are a Meridian Bank support specialist. Handle withdrawals, disputes, opt-out "
                "requests, identity concerns, or account changes outside onboarding. Be brief. "
                "Do not give financial advice."
            ),
            introduction="This is Meridian support — I can help with that.",
            max_tokens=250,
        ),
    )

    prompt = f"""
You are an onboarding assistant for Meridian, a digital bank. You call customers who
started opening an account but didn't finish, to collect the last required details.

This is regulated outbound — stay inside these rules:
- This is NOT debt collection. If asked for financial or investment advice, politely decline
  and steer back to finishing the account — do not transfer for this.
- At the start, call check_call_compliance. If it says not allowed, apologize and end the call.
- Verify the customer's date of birth before discussing any account details.
- Collect only the missing onboarding fields (minimum necessary). Do not ask for unrelated
  financial or sensitive data (no full account numbers, balances, SSN, or card numbers).
- Confirm all collected fields once, then call submit_kyc_details.
- Call transfer_to_support only when the customer wants to withdraw or not continue, disputes the
  account, reports an identity problem, is distressed, or needs an account change outside this flow.
- Never claim the mock tools are production systems.

Call context:
Name: {context["user_name"]}
Account ID: {context["account_id"]}
Reason: {context["reason"]}
DOB on file: {context["date_of_birth"]}
Completed: {", ".join(context["completed_steps"])}
Missing: {", ".join(context["missing_fields"])}
Region: {context["region"]}
"""

    return LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[
            *build_tools(context),
            agent_as_handoff(
                support_agent,
                name="transfer_to_support",
                description="Transfer when the user needs help outside this onboarding flow.",
                handoff_message="I am transferring you to support now.",
            ),
            end_call,
        ],
        config=LlmConfig(
            introduction=(
                f"Hi {context['user_name']}, this is Meridian Bank's onboarding team "
                f"calling about your {context['reason']}. Is now a good time for a quick check?"
            ),
            system_prompt=prompt,
            max_tokens=400,
        ),
    )


async def pre_call_handler(call_request: CallRequest):
    # Optional hook that runs once before the call connects — here it just picks the
    # TTS voice and STT language. The per-call data is read later, in get_agent, from
    # call_request.metadata. (Default voice id below is Cartesia's "Friendly Host".)
    return PreCallResult(
        config={
            "tts": {"voice": os.getenv("CARTESIA_VOICE_ID", "910fb75e-1d20-4840-ac63-ac6b26a71bdc")},
            "stt": {"languages": ["en"]},
        },
    )


app = VoiceAgentApp(get_agent=get_agent, pre_call_handler=pre_call_handler)


if __name__ == "__main__":
    app.run()
