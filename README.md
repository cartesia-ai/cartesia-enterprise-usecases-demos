# 10 Enterprise Voice Workflows You Can Build with Cartesia

This guide shows ten common enterprise use cases for Cartesia speech models and voice agents that we are seeing deployed in industry today.

The first three use cases call Cartesia models directly. Use cases four through six, eight, and nine use the Line SDK. Use case seven uses Cartesia Managed Agents. The tenth pairs Cartesia voices with digital avatars.

## Get the code

All ten examples live in **[this repo](https://github.com/cartesia-ai/cartesia-enterprise-usecases-demos)** — clone it to follow along. See [Setup](#setup-for-all-use-cases) below for prerequisites.

## Table of Contents

- [1. Domain-Specific Dictation and Notes](#1-domain-specific-dictation-and-notes)
- [2. Multilingual Training and Practice](#2-multilingual-training-and-practice)
- [3. Voice Feedback Surveys](#3-voice-feedback-surveys)
- [4. Inbound Support Triage](#4-inbound-support-triage)
- [5. Healthcare Appointment Booking](#5-healthcare-appointment-booking)
- [6. Banking KYC Follow-Up](#6-banking-kyc-follow-up)
- [7. Sales Role-Play and Coaching](#7-sales-role-play-and-coaching)
- [8. Sales Qualification](#8-sales-qualification)
- [9. Internal HR Helpdesk](#9-internal-hr-helpdesk)
- [10. Voice for Digital Avatars](#10-voice-for-digital-avatars)
- [Setup For All Use Cases](#setup-for-all-use-cases)
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

**Tip:** Sonic-3.5 doesn't need an emotion setting — it infers tone from the surrounding context. The `SCENARIOS` lines in the script give it that context: they describe the moment ("greeting a customer with a positive energy") and quote the actual words to speak, so the read comes out warm rather than flat. Try the same line with and without that framing to hear the difference.

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



## 7. Sales Role-Play and Coaching



### What you're building

Sales reps get good at handling objections by doing it, but a live prospect is a bad place to practice. This **Managed Agent** is a practice partner: it plays a hesitant prospect — a mid-market ops manager who isn't sure they need the product — so a rep can rehearse the pitch and work through the pushback out loud, as many times as they want. When the rep wraps up or asks for feedback, the agent drops the character and gives a short coaching scorecard. Same agent, two modes, no real deal on the line.

### Why use Cartesia here

A role-play only helps if it feels like a real call — spoken, in the moment, with someone who pushes back. Cartesia Managed Agents combine Ink-2 transcription, a managed LLM, and Sonic-3.6 speech so the rep practices the way they'll actually sell, not by typing. Cartesia hosts that full  e2e voice agent and conversation runtime; this example only supplies the instructions and one mock scoring tool.

### Why the agent needs a tool at all

The agent could judge the call by itself — models will happily tell a rep how they did. You don't want that. Improvised feedback shifts from call to call, can't be compared between two reps, and rests on whatever the model happened to notice.

`score_call` moves that judgement out of the model and into your system. Every rep gets measured against the same rubric, the result is something you can store and track over a quarter, and the score can draw on what the model can't see: CRM outcomes, the criteria your sales leaders actually agreed on, how this rep scored last month.

That is what a webhook tool adds to an agent. Not plumbing — grounding. It's the difference between a convincing role-play and training you can manage.

### Step-by-step workflow

1. The agent speaks first, in character as the prospect, and raises realistic objections — price, priority, an existing workaround, needing buy-in from others.
2. The rep runs discovery, makes the pitch, and handles the pushback.
3. When the rep says they're done or asks for feedback, the agent calls `score_call` (mock) and switches out of character.
4. As a coach, the agent reads back a short scorecard — discovery, objection handling, value articulation, next step — with one overall tip, then ends the call.



### The two files, and why there are two

Cartesia hosts the conversation. The scoring logic is your business logic and so it lives in your server. So a webhook tool calls back out to your server (in this example using the free cloudflare tunnel). That split is the whole architecture, so the folder has one file per side:


| File                   | What it is                                                      | When it runs                                |
| ---------------------- | --------------------------------------------------------------- | ------------------------------------------- |
| `score_call_server.py` | Your backend. An HTTP endpoint returning the scorecard.         | Running the whole time the agent is in use. |
| `provision_agent.py`   | One-time setup. Creates the tool and the agent in your account. | Once. Then never again.                     |


In production the first one is a service you deploy and the second is a setup script you run from CI. Nothing in this example runs "the call" — Cartesia does that.

### Run it in three minutes

**First, open three terminal windows.** Two of them stay open the whole time you're using the agent, which is why they can't share one window:


|                | What runs there                           | How long                                         |
| -------------- | ----------------------------------------- | ------------------------------------------------ |
| **Terminal 1** | Your backend, `score_call_server.py`.     | Stays running. Closing it breaks the scorecard.  |
| **Terminal 2** | The tunnel, `cloudflared`.                | Stays running. Closing it kills your public URL. |
| **Terminal 3** | The checks and the one-off setup command. | Free. Reuse it for anything.                     |


Terminals 1 and 2 are both blocking processes — they print a line and then sit there, which is what you want. Neither will return you to a prompt.

This is a local-development shape, not production. Deployed for real, Terminal 1 is a service running somewhere on its own, Terminal 2 doesn't exist at all, and Terminal 3 is a step in CI you run once.

**1. Start your backend.** (Terminal 1) No API key here — this half never calls Cartesia. Cartesia calls it.

```bash
uv run python examples/07_sales_roleplay/score_call_server.py
```

It prints `score_call endpoint listening on http://127.0.0.1:8000/score-call` and stays running. Leave it.

This is a plain web server and nothing else. It answers `POST /score-call` with a fixed scorecard — **the same JSON every time, to anyone who asks, whatever they send it**. `build_scorecard()` doesn't read the request at all. It knows nothing about agents, calls or conversations, which is what makes it a mock and why you can test it on its own, before any agent exists.

**2. Expose it with a tunnel.** (Terminal 2)

Cartesia calls your endpoint over the internet, so it needs a public HTTPS URL. `http://127.0.0.1:8000` only exists on your machine. A tunnel gives you a temporary public URL that forwards to it. This is a local-development step — in production your service is already deployed at a real address and there's no tunnel involved.

Install `cloudflared` for your OS from [Cloudflare's downloads page](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/). No Cloudflare account is needed. Then run:

```bash
cloudflared tunnel --url http://localhost:8000
```

It prints a box with a URL in it:

```
+--------------------------------------------------------------------------------------------+
|  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):    |
|  https://responsibilities-affiliates-lived-polyphonic.trycloudflare.com                      |
+--------------------------------------------------------------------------------------------+
```

That URL is what Cartesia will call. A request to it reaches Cloudflare, which forwards it down the tunnel to `http://localhost:8000` on your machine — so your laptop answers, without being exposed to the internet itself.

Copy it and leave the tunnel running. You get a different random URL every time you restart `cloudflared`, which matters in step 3.

**Then wait about ten seconds before using it.** The `trycloudflare.com` hostname was created seconds ago and the internet's DNS hasn't caught up yet — cloudflared says as much in the box, "it may take some time to be reachable." Requests sent too early fail with `Could not resolve host`, which looks like a broken setup but isn't.

Once you've waited, check the whole path end to end. This one goes in **Terminal 3** — Terminals 1 and 2 are both busy holding processes open:

```bash
curl -s -X POST https://YOUR-TUNNEL-URL/score-call
```

**What this checks is the path, not the agent.** For the scorecard to work during a call, a request has to travel from the public internet to your laptop: DNS, then Cloudflare's edge, then the tunnel in Terminal 2, then your server. That's four things that can be broken. This `curl` walks all four now, while a failure still has one possible cause.

The `curl` sends no data, and doesn't need to — `build_scorecard()` never looks at the request, so an empty POST runs the same code a real call would. (If you later replace the mock with scoring that reads a transcript, send a sample body here instead.)

**The scorecard that comes back is not a result.** Nothing has been spoken or scored. The endpoint returns that same JSON to anybody who asks. Getting it here only means the pipe is open.

A pass is scorecard JSON here plus a `[score_call]` line in Terminal 1. Anything else tells you what to fix:


| What you see             | What it means                                    | What to do                                                     |
| ------------------------ | ------------------------------------------------ | -------------------------------------------------------------- |
| `Could not resolve host` | DNS hasn't caught up with the new hostname.      | Wait ten seconds, run it again.                                |
| `502`                    | Tunnel is up, nothing is listening on port 8000. | Check Terminal 1 is still running, and that it says port 8000. |
| `404`                    | Wrong path.                                      | Use `/score-call`, with the hyphen.                            |
| `501`                    | You sent a GET, not a POST.                      | Keep `-X POST` in the command.                                 |
| Nothing, then a timeout  | Tunnel died.                                     | Check Terminal 2; restart it and use the new URL.              |
| `200` and scorecard JSON | Working.                                         | Go to step 3.                                                  |


Don't skip ahead on a failure. Provisioning will still succeed and the agent will still role-play — it just dies at the scorecard, mid-call, where the cause is invisible.

**3. Create the agent.** (Terminal 3)

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"

uv run python examples/07_sales_roleplay/provision_agent.py \
  --webhook-base-url https://<<<<<YOUR-TUNNEL-URL>>>>>>>
```

It prints an `agent_id`. That agent is live immediately — there is no deploy step.

**4. Talk to it.** Open [Managed Agents in the Playground](https://play.cartesia.ai/agents), select the agent by that id, and start the call:

- It opens in character. Pitch your product and answer its questions.
- When it pushes back — "the price feels high for what we'd use," "it's not a priority this quarter" — handle the objection.
- Say "I'm done — how did I do?" It drops the persona, calls `score_call`, reads the scorecard, and ends the call.

Watch Terminal 1 while it does that. The `[score_call]` line printing there is a live voice call reaching your laptop.

**Where the scorecard ends up.** Nowhere. The agent speaks it and hangs up — Cartesia doesn't keep it, and the spoken version is gone with the call. Nothing is written to disk here, because this scorecard is a constant and saving the same four numbers repeatedly would tell you nothing.

What you do get is the exchange, in Terminal 1:

```
[score_call] 2026-09-11T05:05:45Z from 127.0.0.1
  in : {"call_id":"abc123","tool":"score_call"}
  out: 200, discovery 3, objection_handling 4, value_articulation 2, next_step 3
```

The `in:` line is worth watching — it's what Cartesia actually posts to a webhook tool, which you can't see from anywhere else.

That absence is the thing to take from this example: **whatever your endpoint returns is spoken once and then lost.** If a score has to survive the call, your endpoint is what has to write it down. Swap `build_scorecard()` for real transcript scoring, have it persist to your database, and everything else here stays as it is.

> **Before you re-run step 3:** the tunnel URL is baked into the tool when it is created, and nothing updates it afterwards. Restart the tunnel and you get a new URL so you can update the webhook settings of your deployed voice agent on the Cartesia playground, under the Managed Agents section.

### Changing the prompt on an existing agent

Re-running the provisioning command with `--webhook-base-url` always creates a **new** agent. To change the one you already have, edit the file and pass its id instead:

```bash
uv run python examples/07_sales_roleplay/provision_agent.py --agent-id YOUR_AGENT_ID
```

That `PATCH`es the whole local config, so an edit to the prompt, the greeting, the model, the token ceiling, the language, the voice or `end_call` all go through this one command. `config.tools` is left out on purpose, so the agent keeps the `score_call` tool it was created with.

`score_call` returns the same fixed scorecard every time. Replace `build_scorecard()` with transcript-based scoring for production; nothing else has to change.

Run the tests with:

```bash
uv run python -m unittest discover -s examples/07_sales_roleplay -p "test_*.py"
```

Learn more about [Managed Agents](https://docs.cartesia.ai/agents/introduction) and [webhook tools](https://docs.cartesia.ai/agents/webhook-tools).

### Take it live

The agent is live as soon as the provisioning command creates it. To receive phone calls, assign it a number in the Playground. See [connect a phone number](https://docs.cartesia.ai/line/integrations/telephony/phone-numbers).

---



## 8. Sales Qualification



### What you're building

When a prospect calls your sales line, someone has to work out fast whether they're a real opportunity, and get the good ones to a rep before they cool off. This **Line** agent runs that first qualifying conversation: it runs the four checks sales teams call BANT — budget, authority (who owns the decision), need, and timeline — logs the lead, and routes. A qualified lead is handed to an account executive on the same call; everyone else is captured for follow-up. It's the same intake-and-route shape as the support triage example, pointed at revenue instead of tickets.

### Why use Cartesia here

Leads cool off fast — someone who reaches out is most interested right then, not an hour later when a rep calls back. A voice agent answers straight away and asks the same qualifying questions every time, so a real opportunity reaches a salesperson while the interest is still there, and the rep's time goes to the leads worth following up. Ink-2 transcribes the caller, Sonic-3.5 voices the replies, and Line hands qualified leads to a human account executive, who picks up the same conversation.

### Step-by-step workflow

1. The agent greets the caller and asks what they're trying to solve.
2. It works through BANT conversationally — need, authority, budget, timeline — plus name and company.
3. It calls `capture_lead` (mock CRM) with the details and whether the lead is qualified.
4. If qualified, `transfer_to_account_executive` hands the live call to an AE. If not, the agent says a rep will follow up by email and ends the call.



### Run it

Set your keys, then start the server:

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

uv run python examples/08_sales_qualification/08_sales_qualification.py
```

In a second terminal — `cartesia chat` opens a text conversation with the running agent on port 8000. The agent greets first:

```bash
cartesia chat 8000
```

Try it:

- Be a real opportunity: "We're a 200-person company, called ACME Traders, and our analytics are a mess, we're evaluating tools this quarter and I own the budget." Answer its questions and watch it qualify you and hand you to an account executive.
- Start a fresh `cartesia chat` and be a poor fit: "I'm a student doing research, no budget, just curious." It logs you as not qualified and ends with an email follow-up instead of transferring.

A qualified lead here goes to a live account exec. You could just as easily book them a meeting — drop in the scheduling flow from the healthcare booking example (use case 5), which confirms a slot and writes it back.

Learn more about [Line tools and handoffs here.](https://docs.cartesia.ai/line/sdk/tools)

### Take it live

`cartesia chat` is local text only. To hear the agent on a real phone call, run `cartesia deploy`, then call it from the [Playground](https://play.cartesia.ai/agents) or with `cartesia call +1XXXXXXXXXX`. See [Deploy and talk to your agent](https://docs.cartesia.ai/line/start-building/quickstart).

---



## 9. Internal HR Helpdesk



### What you're building

Every company runs an internal helpdesk for the same repetitive questions — how much PTO do I have, what's the expense limit, how do I get VPN access. This **Line** agent answers them from your own policy docs: using RAG, it looks up the question in a Cartesia [knowledge base](https://docs.cartesia.ai/line/knowledge-base) and answers from what's there, instead of guessing. Anything sensitive or personal — a harassment concern, a pay dispute, leave specifics — goes to a human in HR. Point the same agent at a different folder of docs and it's an IT helpdesk, a self-serve onboarding guide, or a SaaS provisioning desk; only the documents change.

### Why use Cartesia here

The pieces fit together with no extra plumbing: Ink-2 transcribes the employee, Sonic-3.5 voices the replies, and Line's knowledge base retrieves from your docs (RAG) so answers stay grounded in your actual policies, not the model's training. Because the docs live in the Cartesia dashboard, the HR or IT team that owns them keeps them current — no prompt edits, no redeploy.

### Step-by-step workflow

1. The employee asks a question.
2. For a general policy question, the agent calls `lookup_hr_policy`, which queries the knowledge base, and answers from the result.
3. If the lookup returns nothing — or the knowledge base isn't connected yet — the agent says the policy isn't available and offers to connect the employee with HR. It doesn't guess.
4. Sensitive or personal matters hand off to a human with `transfer_to_hr_specialist`.



### Deploy and connect your knowledge base

The knowledge base is tied to a specific deployed agent. So for this one we recommend deploying to the Cartesia hosted platform and attaching a knowledge base — a couple of simple policy docs (or AI-generated ones) are enough to simulate the scenario. You can still run it locally with `cartesia chat`, but since local chat has no knowledge base, the lookup just tells the user to deploy the agent and connect a knowledge base. That's also a useful pattern in itself — it's the no-guessing behavior at work.

Here's how you can deploy:

1. Follow the [quickstart](https://docs.cartesia.ai/line/start-building/quickstart) to scaffold and deploy an agent (`cartesia init`, then `cartesia deploy`), replacing the generated `main.py` with `examples/09_hr_helpdesk/09_hr_helpdesk.py`.
2. In the [Playground](https://play.cartesia.ai/knowledge-base), create a knowledge base, upload your policy docs, and attach it to this agent. Sample HR docs are in `examples/09_hr_helpdesk/kb_docs/` to get you started. Whoever owns the content (HR, IT) maintains it here — no code.

Now `lookup_hr_policy` returns real answers from your docs.

### Try it

Talk to the deployed agent in the [Playground](https://play.cartesia.ai/agents) or with `cartesia call +1XXXXXXXXXX`:

- Ask a policy question — "How much parental leave do I get?" The agent looks it up in your knowledge base and answers from the doc.
- Ask about something sensitive — "I want to report a problem with my manager." It hands you to a human in HR.

You can run it locally the same way as the earlier examples (`uv run python examples/09_hr_helpdesk/09_hr_helpdesk.py`, then `cartesia chat 8000`) if you want to see the conversation and the handoff — but policy lookups only return real answers once a knowledge base is attached to the deployed agent.

---



## 10. Voice for Digital Avatars

Give your Cartesia voice agents a face. Pair Sonic-3.5's low-latency, natural and emotive speech with an on-screen avatar to build presenters for demos, training, kiosks, and virtual reception. See a great example of this pairing in [this video](https://drive.google.com/file/d/1eKTAyxhv91o7YViGYOXhveGVI6ernqtO/view) from one of our partners, [Anam](https://anam.ai).

---



## Setup For All Use Cases

Install dependencies:

```bash
uv sync
```

Set your Cartesia key (required for all examples):

```bash
export CARTESIA_API_KEY="your-cartesia-api-key"
```

For Line examples (4–6 and 8–9), also set an Anthropic key:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```



## What next

If you're ready to build or extend your own enterprise-grade voice AI applications, reach out to us at **[business@cartesia.ai](mailto:business@cartesia.ai)**.