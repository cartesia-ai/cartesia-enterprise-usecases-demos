"""Voice feedback survey: generate a survey question with Sonic-3.5, transcribe the answer with Ink-2.

Usage:
    uv run python 03_voice_feedback_surveys.py --audio answer.wav

Docs:
    Sonic-3.5 TTS:       https://docs.cartesia.ai/build-with-cartesia/tts-models/latest
    Ink-2 STT:           https://docs.cartesia.ai/build-with-cartesia/stt-models/latest
    STT websocket API:   https://docs.cartesia.ai/api-reference/stt/websocket
"""

import argparse
import asyncio
import json
import os
import sys
import wave
from pathlib import Path

from cartesia import AsyncCartesia, Cartesia

SCRIPT_DIR = Path(__file__).parent
CHUNK_LENGTH_MS = 100

SURVEY_QUESTION = (
    "Thanks for finishing setup. "
    "What slowed you down, and what should we improve first?"
)

DEFAULT_VOICE_ID = "e07c00bc-4134-4eae-9ea4-1a55fb45746b"
QUESTION_OUTPUT = SCRIPT_DIR / "survey_question.wav"


# ── TTS: generate the survey question as audio ───────────────────────

def generate_question_audio(api_key: str, text: str, output: Path, voice_id: str) -> None:
    client = Cartesia(api_key=api_key)
    resp = client.tts.generate(
        model_id="sonic-3.5",
        transcript=text,
        voice={"mode": "id", "id": voice_id},
        output_format={"container": "wav", "encoding": "pcm_s16le", "sample_rate": 16000},
        language="en",
    )
    resp.write_to_file(str(output))


# ── STT: stream answer audio to Ink-2 ───────────────────────────────

def load_wav_chunks(path: Path) -> tuple[int, list[bytes]]:
    """Read a wav file and split it into small time-slices for streaming.

    Ink-2 websocket STT expects audio sent in near-real-time pieces, not
    all at once. This function reads the wav, checks it's the right format
    (mono, 16-bit, uncompressed), then chops the raw audio bytes into
    100 ms chunks that we can drip-feed to the websocket.

    Returns the sample rate and the list of chunks.
    """
    with wave.open(str(path), "rb") as wf:
        # Ink-2 needs mono (1 channel), 16-bit (2 bytes/sample), uncompressed PCM
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            raise RuntimeError(f"{path.name}: expected mono 16-bit PCM wav")
        framerate = wf.getframerate()
        # "How many frames in 100 ms of audio?"
        # framerate = frames per second (from the wav file header).
        # Multiply by CHUNK_LENGTH_MS to scale by the chunk duration.
        # Divide by 1000 to convert milliseconds to seconds.
        # e.g. 16000 fps x 100 ms / 1000 = 1600 frames per chunk.
        frames_per_chunk = framerate * CHUNK_LENGTH_MS // 1000
        chunks: list[bytes] = []
        while data := wf.readframes(frames_per_chunk):
            chunks.append(data)
    return framerate, chunks


async def transcribe_with_ink2(api_key: str, rate: int, chunks: list[bytes]) -> str:
    client = AsyncCartesia(api_key=api_key)
    transcript = ""
    async with client.stt.manual_finalize.websocket(
        encoding="pcm_s16le", model="ink-2", sample_rate=rate,
    ) as ws:
        for chunk in chunks:
            await ws.send_raw(chunk)
            await asyncio.sleep(CHUNK_LENGTH_MS / 1000)
        await ws.send("finalize")
        await ws.send("close")
        async for event in ws:
            if event.type == "transcript" and event.is_final:
                transcript += event.text
    return transcript.strip()


# ── Stub for downstream feedback analysis ────────────────────────────

def extract_themes_and_sentiment(transcript: str) -> dict[str, object]:
    # Mocked theme/sentiment pipeline — replace with your own.
    _ = transcript
    return {
        "themes": ["onboarding friction", "unclear error messages", "documentation gaps"],
        "sentiment": "mixed",
        "analysis_note": "Mocked — replace with your own theme and sentiment pipeline.",
    }


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Voice feedback survey (Sonic-3.5 + Ink-2).")
    parser.add_argument("--audio", required=True, help="Answer .wav to transcribe with Ink-2")
    args = parser.parse_args()

    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        print("error: set CARTESIA_API_KEY before running.", file=sys.stderr)
        raise SystemExit(2)

    voice_id = os.environ.get("CARTESIA_VOICE_ID", DEFAULT_VOICE_ID)

    # TTS: generate the spoken survey question
    generate_question_audio(api_key, SURVEY_QUESTION, QUESTION_OUTPUT, voice_id)
    print(f"Wrote survey question audio → {QUESTION_OUTPUT}", file=sys.stderr)

    # STT: transcribe the answer
    audio = Path(args.audio)
    if not audio.is_absolute():
        audio = SCRIPT_DIR / audio
    if not audio.exists():
        print(f"error: file not found: {audio}", file=sys.stderr)
        raise SystemExit(2)

    rate, chunks = load_wav_chunks(audio)
    print(
        f"Streaming {audio.name} to Ink-2 as {len(chunks)} {CHUNK_LENGTH_MS}ms-chunks -- i.e,"
        f"(~{len(chunks) * CHUNK_LENGTH_MS / 1000:.0f}s of audio, sent in real time)…",
        file=sys.stderr,
        flush=True,
    )
    transcript = asyncio.run(transcribe_with_ink2(api_key, rate, chunks))
    if not transcript:
        print("error: Ink-2 returned an empty transcript.", file=sys.stderr)
        raise SystemExit(1)

    analysis = extract_themes_and_sentiment(transcript)
    print(json.dumps({
        "survey_question_text": SURVEY_QUESTION,
        "customer_answer_transcript": transcript,
        **analysis,
    }, indent=2))


if __name__ == "__main__":
    main()
