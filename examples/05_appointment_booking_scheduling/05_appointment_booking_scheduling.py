"""Telehealth appointment booking with Cartesia Line.

One of the 10 enterprise voice use cases in the Cartesia guide (see README).

A scheduling assistant for a telehealth clinic: it books video visits, collects
only the minimum details needed (minimum-necessary), and hands clinical questions
to the care team. It never gives medical advice.

Compliance note: this is a DEMO. Identity checks, the calendar, and PHI handling
are mocked. A real deployment runs under a BAA with audit logging, access
controls, and your own consent/retention policy. Cartesia's voice models meet
HIPAA and SOC 2 requirements (https://cartesia.ai/legal/safety), so the speech
layer is not the compliance gap — your data handling around it is.

Tool types used below (loopback, agent_as_handoff):
  https://docs.cartesia.ai/line/sdk/tools

Setup:
  uv add cartesia-line
  export CARTESIA_API_KEY="your-cartesia-api-key"
  export ANTHROPIC_API_KEY="your-anthropic-api-key"

Run:
  uv run python examples/05_appointment_booking_scheduling/05_appointment_booking_scheduling.py
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
from line.voice_agent_app import AgentEnv, CallRequest, VoiceAgentApp


# Mock telehealth openings, keyed by day of week so the demo never goes stale.
# A real EHR / scheduling API would return concrete dates; resolve day -> date there.
AVAILABILITY = [
    {"slot_id": "slot_001", "day": "Monday", "time": "09:00", "clinician": "Dr. Lena Ortiz", "visit_type": "New patient"},
    {"slot_id": "slot_002", "day": "Tuesday", "time": "14:30", "clinician": "Dr. Sam Park", "visit_type": "Follow-up"},
    {"slot_id": "slot_003", "day": "Wednesday", "time": "11:00", "clinician": "Dr. Lena Ortiz", "visit_type": "Follow-up"},
    {"slot_id": "slot_004", "day": "Thursday", "time": "10:15", "clinician": "Dr. Sam Park", "visit_type": "New patient"},
    {"slot_id": "slot_005", "day": "Friday", "time": "15:45", "clinician": "Dr. Lena Ortiz", "visit_type": "Follow-up"},
]

# In-memory booking store.
booking_state: dict = {}

# Reasoning model. The "anthropic/" prefix routes the call to Anthropic via
# LiteLLM; without it the SDK defaults to OpenAI.
MODEL = "anthropic/claude-sonnet-4-5"
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # see guide Setup


@loopback_tool
async def get_availability(ctx: ToolEnv) -> str:
    """Returns JSON: {"slots": [...], "note": str} — every open telehealth slot.

    A real EHR API would filter server-side by a requested date range; this mock
    returns all openings and lets the agent match the caller's preferred day.
    """
    logger.info("[get_availability()] Listing telehealth openings")
    return json.dumps({"slots": AVAILABILITY, "note": "Mock data — replace with EHR / scheduling API."})


@loopback_tool
async def confirm_booking(
    ctx: ToolEnv,
    slot_id: Annotated[str, "Slot ID chosen by the caller from get_availability."],
    name: Annotated[str, "Patient's full name."],
    date_of_birth: Annotated[str, "Patient's date of birth — the visit identifier."],
    callback_phone: Annotated[str, "Callback number for the visit link."],
) -> str:
    """Returns JSON. On success: {"ok": True, "confirmation_id": str, "slot": {...}}.
    If slot_id is unknown: {"ok": False, "error": "Slot not found."}.
    """
    # Mock booking confirmation. Stores only the minimum needed to book the visit.
    logger.info(f"[confirm_booking()] Booking {slot_id} for {name}")
    slot = next((s for s in AVAILABILITY if s["slot_id"] == slot_id), None)
    if not slot:
        return json.dumps({"ok": False, "error": "Slot not found."})
    booking_state.update(
        {"name": name, "date_of_birth": date_of_birth, "callback_phone": callback_phone, "slot": slot, "status": "confirmed"}
    )
    confirmation_id = f"VISIT-{len(booking_state):04d}"
    print(json.dumps({"confirmed_booking": booking_state}, indent=2))
    return json.dumps({"ok": True, "confirmation_id": confirmation_id, "slot": slot})


async def get_agent(env: AgentEnv, call_request: CallRequest):
    # Care team handoff target: clinical questions, no suitable slot, or sensitive cases.
    care_team_agent = LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[end_call],
        config=LlmConfig(
            introduction="This is the care team — I can help with that.",
            system_prompt=(
                "You are a member of the telehealth clinic's care team. Handle calls the "
                "scheduling assistant could not: clinical questions, no suitable slot, or "
                "sensitive requests. Be brief. Do not give medical advice on this call — "
                "arrange a clinician follow-up instead."
            ),
        ),
    )

    return LlmAgent(
        model=MODEL,
        api_key=API_KEY,
        tools=[
            get_availability,
            confirm_booking,
            agent_as_handoff(
                care_team_agent,
                name="transfer_to_clinic_staff",
                description="Transfer clinical questions, no-slot situations, service errors, or sensitive cases to the care team.",
                handoff_message="Let me bring in the care team for you.",
            ),
            end_call,
        ],
        config=LlmConfig(
            introduction="Thanks for calling the telehealth clinic. I can help you book an appointment — is this a new-patient or follow-up visit?",
            system_prompt="""\
You are a scheduling assistant for a telehealth clinic. Every appointment is a video visit; you book these only.

Boundaries (this is a healthcare call — stay inside them):
- You are not a clinician. Do not give medical advice or discuss symptoms, diagnoses, or medications.
- Collect only what is needed to book the visit (minimum necessary): name, date of birth, a callback number, and the visit type.
- If the caller describes symptoms or asks a clinical question, do not answer — call transfer_to_clinic_staff.

Flow:
1. Ask for the caller's name and the visit type (new patient or follow-up).
2. Ask which day of the week works, then call get_availability to list all open slots.
3. Compare the caller's preferred day against the open slots. Offer the ones that fit (day, time, clinician) and let them choose. If nothing fits (e.g. a weekend — the clinic is open Mon-Fri), say so and offer the open days instead.
4. Collect date of birth and a callback number, read them back to confirm, then call confirm_booking.
5. Read back the confirmed visit details.
6. If you cannot book — no suitable slot, get_availability errors, or a request outside scheduling — call transfer_to_clinic_staff.
7. This demo uses mock availability — do not claim it is a real calendar or EHR.
""",
            max_tokens=400,
        ),
    )


app = VoiceAgentApp(get_agent=get_agent)


if __name__ == "__main__":
    app.run()
