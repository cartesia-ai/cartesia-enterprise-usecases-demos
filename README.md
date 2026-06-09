# 6 Enterprise Voice Workflows You Can Build with Cartesia

This guide shows six common enterprise use cases for Sonic-3.5 (TTS), Ink-2 (STT), and Line (voice agent framework), that we are seeing deployed in industry today.

The first three use cases are Cartesia model-only, via the API. The last three use Cartesia's Line agents SDK.

The [Setup](#setup) section lists the prerequisites you need to run the sample code locally. All the examples live in [this repo](https://github.com/cartesia-ai/cartesia-enterprise-usecases-demos).

## Table of Contents

- [1. Domain-Specific Dictation and Notes](#1-domain-specific-dictation-and-notes)
- [2. Multilingual Training and Practice](#2-multilingual-training-and-practice)
- [3. Voice Feedback Surveys](#3-voice-feedback-surveys)
- [4. Inbound Support Triage](#4-inbound-support-triage)
- [5. Healthcare Appointment Booking](#5-healthcare-appointment-booking)
- [6. Banking KYC Follow-Up](#6-banking-kyc-follow-up)
- [Setup](#setup)
- [What next](#what-next)

## 1. Domain-Specific Dictation and Notes

### What you're building

Dictation tool for jargon-heavy workflows — field reports, clinical notes, legal transcripts, support summaries. **Ink-2** turns your spoken words into text, with industry terms intact.

### Why use Cartesia here

Generic STT mangles specialized vocabulary. Ink-2 gets terms like `feeder breaker`, `contraindication`, and `amicus curiae` right.

### Step-by-step workflow

The script:

1. loads the audio sample you pass with `--audio`. We have included some samples for convenience, generated with Sonic-3.5 TTS.
2. chunks the audio down to 100ms slices,  and streams it to Ink-2 over the [websocket STT API](https://docs.cartesia.ai/api-reference/stt/websocket) and builds the transcript.
3. prints the transcript and saves it to a `.txt` file next to the sample.

See [Compare STT endpoints](https://docs.cartesia.ai/use-the-api/compare-stt-endpoints) for when to use the websocket path versus batch.

### Run it

Set your key, then pass `--audio` with a sample in `examples/01_domain_dictation_notes/`:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"

uv run python examples/01_domain_dictation_notes/01_domain_dictation_notes.py --audio legal.wav
```

The provided samples are generated using Sonic-3.5, and are mono 16-bit PCM `.wav`. Play one first — e.g. open `legal.wav` — to hear the source audio before you transcribe it.

**Output** 

The script prints JSON to stdout:

- `audio` — sample file that was transcribed
- `domain` — extracted from audio filename (`field_ops`, `healthcare`, `legal`, `support`)
- `transcript` — Ink-2's output; read it to see the industry terms came through intact
- `transcript_file` — name of the saved transcript text file (eg `<legal | healthcare>-transcribed.txt` )

The bundled wav samples were generated with Sonic-3.5 Text-to-Speech. You can use your own recorded .wav files if you wish.

Also try `field_ops.wav`, `healthcare.wav`, or `support.wav` — same command, different sample.

**CLI Flags**


| Argument  | Required | Description                                                                                                                                                 |
| --------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--audio` | yes      | Sample filename or path. Relative paths resolve under `examples/01_domain_dictation_notes/`. Stem must be `field_ops`, `healthcare`, `legal`, or `support`. |


Learn more about [Ink 2 here.](https://docs.cartesia.ai/build-with-cartesia/stt-models/latest)

---

## 2. Multilingual Training and Practice

### What you're building

Turn your training scripts into spoken audio in any supported language. For example, an enablement team writes a customer-greeting script, an onboarding walkthrough, or a sales-pitch line once. They then use **Sonic-3.5** to generate the audio in natural-sounding English, Spanish, French, or another supported language — each in a voice native to it. This scales your team's L&D. 

### Why use Cartesia here

Normally you'd hire a voice actor and book studio time for each language, and go back to the studio every time the script changes. That's expensive, especially if you move fast and a lot of training content goes stale. Sonic-3.5 generates the audio straight from text, so you can produce the same script in any supported language and just regenerate it when the wording changes.

### Step-by-step workflow

1. Pick a language and built-in scenario (or pass your own text).
2. Call Sonic-3.5 TTS to generate the spoken audio.
3. Write the WAV file, ready to drop into the training module.

### Run it

Set your key, then pass `--language` with a built-in scenario in `examples/02_multilingual_training_practice/`:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"

uv run python examples/02_multilingual_training_practice/02_multilingual_training_practice.py --language fr
```

**Output**

Prints JSON to stdout and writes the WAV into the script directory:

- `text` — the line that was generated
- `language` — BCP-47 code used
- `voice_id` — the native voice used for that language
- `output_file` — path to the generated WAV
- `model` — `sonic-3.5`

Now run the same line in another language. Each language uses a voice native to it:

```bash
# also try --language en
uv run python examples/02_multilingual_training_practice/02_multilingual_training_practice.py --language es
```

Swap in your own line with `--text`:

```bash
uv run python examples/02_multilingual_training_practice/02_multilingual_training_practice.py --text "Welcome to the team. Let's get you started." --language en
```

With `--text`, the file is saved as `output_<language>.wav` (here `output_en.wav`), so your custom runs don't overwrite the bundled samples. The path is in the JSON `output_file`.

**Tip: the wording shapes the delivery.** Sonic-3.5 picks up tone and emotion cues in the text. Naming the tone (`with positive energy`) and wrapping the spoken line in quotes with natural punctuation makes the read warmer and more expressive. Try the same greeting with and without those cues to hear the difference. The built-in scenarios use this.

**CLI**


| Argument     | Required | Description                                                                                         |
| ------------ | -------- | --------------------------------------------------------------------------------------------------- |
| `--language` | no       | BCP-47 code (default: `en`). Built-in scenarios and voices for `en`, `es`, `fr`.                    |
| `--text`     | no       | Custom text to speak. Overrides the built-in scenario.                                              |
| `--output`   | no       | Output WAV filename. Default `training_<language>.wav`; with `--text` it's `output_<language>.wav`. |


The script uses Sonic-3.5 TTS with Cartesia voices native to the chosen language. For `en`, `es`, or `fr`, just pass `--text`. For any other language, also set `CARTESIA_VOICE_ID` to a voice native to it.

Pre-generated samples included: `training_en.wav`, `training_es.wav`, `training_fr.wav`.

Learn more about [Sonic-3.5 here.](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest)

---

## 3. Voice Feedback Surveys

### What you're building

A post-onboarding survey, delivered by an AI voice agent, that asks one question after setup, captures a spoken reply, and turns it into text the team can review. This example also shows where a downstream feedback analysis pipeline would plug in.

### Why use Cartesia here

Short feedback forms via email get ignored because typing can seem like effort.  Sonic-3.5 generates a consistent survey question as audio. Ink-2 turns the reply into text so the team can review what blocked activation.

### Step-by-step workflow

The script:

1. generates the survey question as `survey_question.wav` with Sonic-3.5.
2. streams the bundled reply file `customer_answer.wav` to Ink-2.
3. prints JSON with the survey question text, transcript, and a stubbed downstream analysis hook.

Ink-2 in this example uses the realtime websocket path, like use case 1. See [Compare STT endpoints](https://docs.cartesia.ai/use-the-api/compare-stt-endpoints).

### Run it

Run the full post-onboarding feedback flow end to end:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"

uv run python examples/03_voice_feedback_surveys/03_voice_feedback_surveys.py --audio customer_answer.wav
```

After the run finishes:

**File created**

- `survey_question.wav` — the survey question audio generated by Sonic-3.5

**Terminal output**

- `survey_question_text` — the survey question text used to generate `survey_question.wav`
- `customer_answer_transcript` — Ink-2's transcription of `customer_answer.wav`
- `themes` — currently mocked theme extraction; swap in your own pipeline
- `sentiment` — currently mocked sentiment analysis; swap in your own pipeline
- `analysis_note` — reminder that the analysis is mocked, not computed from the transcript

`customer_answer.wav` is the bundled customer's response. You can swap in another mono 16-bit PCM `.wav` file.

Learn more about [Sonic-3.5](https://docs.cartesia.ai/build-with-cartesia/tts-models/latest) and [Ink-2](https://docs.cartesia.ai/build-with-cartesia/stt-models/latest).

---

## 4. Inbound Support Triage

### What you're building

The first minute of any product-support call is triage: who's calling, what's wrong, where it should go. This **Line** agent (modeled as a SaaS company, "Acme") runs the triage on the phone conversation — it asks a couple of intake questions, classifies the issue, opens a helpdesk ticket, then **hands the live call off** to one of three specialist agents: billing, technical, or a human queue for anything sensitive.

### Why use Cartesia here

Line runs Cartesia models under the hood — Ink-2 transcribes the caller, Sonic-3.5 voices the replies. It is also the agent framework that orchestrates tool calls that reach into CRMs, and other data stores. Line also handles handoffs to other agents or humans during the call.

### Step-by-step workflow

1. Caller explains the issue.
2. Agent asks for the caller's phone number.
3. Agent calls `lookup_customer` (mock CRM).
4. Agent classifies the request as billing, technical, account, or escalation.
5. Agent calls `create_support_ticket` (mock helpdesk).
6. Agent routes: `transfer_to_billing`, `transfer_to_technical`, or `transfer_to_human`.

### Run it

Set your keys, then start the server:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

uv run python examples/04_inbound_support_triage/04_inbound_support_triage.py
```

In a second terminal — `cartesia chat` opens a text conversation with the running agent on port 8000:

```bash
cartesia chat 8000
```

Walk through one billing support call:

1. Open with "My invoice was double-charged this month."
2. When asked, give the number on file: `555-0100` — it's in the mock CRM, so the lookup succeeds. Give any other number and the lookup fails, so the agent hands off to `transfer_to_human` — mocked here, so it just logs the reason and ends the call.
3. Answer the one follow-up question, then watch it open a ticket and hand the call to billing.

Swap step 1 for "The app keeps crashing when I upload a file." to see it route to the technical specialist instead.

Learn more about [Line tools and handoffs here.](https://docs.cartesia.ai/line/sdk/tools)

The specialists here work from their prompts alone. If you want them answering from your actual policy docs, runbooks, or support FAQs, connect a [knowledge base](https://docs.cartesia.ai/line/knowledge-base) — that's RAG — and the agent looks things up in those docs while it talks.

### Take it live

`cartesia chat` is local text only. To hear the agent on a real phone call, run `cartesia deploy`, then call it from the [Playground](https://play.cartesia.ai/agents) or with `cartesia call +1XXXXXXXXXX`. See [Deploy and talk to your agent](https://docs.cartesia.ai/line/start-building/quickstart).

---

## 5. Healthcare Appointment Booking

### What you're building

Booking a telehealth appointment over the phone — every visit is a video appointment. This **Line** agent takes the call, finds open slots, confirms one, and books it against the patient's name and date of birth. It books appointments; it doesn't diagnose. Any symptom or clinical question goes straight to the care team. The booking workflow is the same one you'd use for a hotel or a field-service window; what changes in healthcare is the guardrails.

### Why use Cartesia here

Healthcare buyers don't open with "what can it do" — they open with "what could go wrong." A voice agent here has to handle patient data carefully, stay in its lane, and never improvise medical advice. Cartesia's voice models meet HIPAA and SOC 2 requirements ([safety](https://cartesia.ai/legal/safety)), so the speech layer — Ink-2 transcribing the caller, Sonic-3.5 voicing the replies — isn't where your compliance risk sits. The agent collects only what it needs to book (minimum-necessary), stays off clinical topics, and hands anything sensitive to a human.

### Step-by-step workflow

1. Caller says what kind of visit they need (new patient or follow-up).
2. Agent asks which day of the week works, then calls `get_availability` (mock EHR/calendar) and matches the caller's day against the open slots.
3. Agent offers the slots that fit and lets the caller choose one.
4. Agent collects name, date of birth, and a callback number, reads them back, then calls `confirm_booking` (mock writeback).
5. Agent reads back the confirmed visit.
6. Clinical questions, no suitable slot, or sensitive cases hand off with `transfer_to_clinic_staff`.

### Run it

Set your keys, then start the server:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

uv run python examples/05_appointment_booking_scheduling/05_appointment_booking_scheduling.py
```

In a second terminal — `cartesia chat` opens a text conversation with the running agent on port 8000:

```bash
cartesia chat 8000
```

Try saying:

- "I'd like to book a follow-up appointment." Then say which day works (e.g. "Monday").
- Pick one of the slots it offers, then give a name, date of birth, and callback number to confirm.
- Now try a medical question instead — "Should I stop taking my medication?" — the agent declines and hands you to the care team.

Learn more about [building Line agents here.](https://docs.cartesia.ai/line/sdk/agents)

### Take it live

`cartesia chat` is local text only. To hear the agent on a real phone call, run `cartesia deploy`, then call it from the [Playground](https://play.cartesia.ai/agents) or with `cartesia call +1XXXXXXXXXX`. See [Deploy and talk to your agent](https://docs.cartesia.ai/line/start-building/quickstart).

---

## 6. Banking KYC Follow-Up

### What you're building

More than half of people who start opening a bank account online never finish — they drop off at a slow form or an awkward step. Often they're nearly there: identity verified, account created, just a few KYC details left (employer, occupation, address) before it can activate. This **Line** agent calls the customer back, confirms who they are, collects just those fields, and saves them — turning an abandoned signup into an active account. Disputes, opt-outs, and identity mismatches hand off to a human. It's regulated outbound — not debt collection, and no financial advice.

### Why use Cartesia here

In financial services an outbound call is a compliance surface: consent, calling-window rules, opt-outs, identity verification, and a hard line against advice or collections. Buyers here fear a compliance slip more than they want the automation. Cartesia's voice models meet SOC 2 requirements ([safety](https://cartesia.ai/legal/safety)) and Cartesia is [GDPR-compliant](https://cartesia.ai/blog/gdpr-compliance), so the speech layer — Ink-2 transcribing the caller, Sonic-3.5 voicing the replies — isn't your exposure; your call rules and data handling are. The agent checks consent before it talks business, verifies identity, asks only for the missing fields, and hands anything sensitive to a human.

### Step-by-step workflow

1. `build_call_context` seeds the call with the customer's partial signup record — who they are and which KYC fields are still missing — from `MOCK_OUTBOUND_CALL_CONTEXT` (or the dialer's call metadata in production).
2. Agent calls `check_call_compliance` (mock consent/calling-window gate).
3. Agent verifies the user's date of birth.
4. Agent explains the reason for follow-up.
5. Agent collects only the missing fields.
6. Agent calls `submit_kyc_details` (mock writeback).
7. Agent hands off disputes or out-of-scope questions to `transfer_to_support`.

### Run it

Set your keys, then start the server:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

uv run python examples/06_outbound_kyc/06_outbound_kyc.py
```

In a second terminal — `cartesia chat` opens a text conversation with the running agent on port 8000. This one is outbound, so the agent speaks first, and has already pulled up your details:

```bash
cartesia chat 8000
```

Follow the main conversation path:

- When it asks if now's a good time, say "Yes, now's fine."
- Give the date of birth on file, `March 15, 1992`, when it verifies you.
- Then provide the missing details it asks for: a delivery address, employer name, and job title.

The conversation can also go other ways. Start a fresh `cartesia chat` for each:

- If you say up front that you've changed your mind and don't want to continue, it hands you over to support.
- If you ask for something it shouldn't touch mid-call — like "Can you recommend a stock?" — it declines and steers you back to finishing the account, without transferring.

Learn more about [outbound calling here.](https://docs.cartesia.ai/line/integrations/telephony/outbound-dialing)

### Take it live

`cartesia chat` is local text only. To hear the agent place a real phone call, run `cartesia deploy`, then trigger it from the [Playground](https://play.cartesia.ai/agents) or with `cartesia call +1XXXXXXXXXX`. See [Deploy and talk to your agent](https://docs.cartesia.ai/line/start-building/quickstart).

---

## Setup

Install dependencies:

```bash
uv sync
```

Set your Cartesia key (required for all examples):

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"
```

For Line examples (4–6), also set an Anthropic key:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

## What next

If you're ready to build or extend your own enterprise-grade voice AI applications, reach out to us at **[support@cartesia.ai](mailto:support@cartesia.ai)**.

