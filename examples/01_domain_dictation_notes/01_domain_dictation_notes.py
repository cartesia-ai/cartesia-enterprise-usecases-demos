"""Transcribe industry dictation samples with Cartesia Ink-2.

Usage:
    uv run python 01_domain_dictation_notes.py --audio field_ops.wav

Docs:
    Ink-2 overview:      https://docs.cartesia.ai/build-with-cartesia/stt-models/latest
    STT endpoint guide:  https://docs.cartesia.ai/use-the-api/compare-stt-endpoints
    Manual STT API ref:  https://docs.cartesia.ai/api-reference/stt/websocket
"""

import argparse
import asyncio
import json
import os
import sys
import wave
from pathlib import Path

from cartesia import AsyncCartesia

SCRIPT_DIR = Path(__file__).parent
CHUNK_LENGTH_MS = 100

# Bundled samples, named by domain. The transcript itself shows whether Ink-2
# kept the jargon intact — no term list needed.
VALID_DOMAINS = {"field_ops", "healthcare", "legal", "support"}


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
        # e.g. 16000 fps × 100 ms / 1000 = 1600 frames per chunk.
        frames_per_chunk = framerate * CHUNK_LENGTH_MS // 1000
        chunks: list[bytes] = []
        while data := wf.readframes(frames_per_chunk):
            chunks.append(data)
    return framerate, chunks


async def transcribe_with_ink2(api_key: str, rate: int, chunks: list[bytes]) -> str:
    """Stream PCM chunks to Ink-2 websocket STT and return the transcript."""
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe industry dictation with Cartesia Ink-2."
    )
    parser.add_argument("--audio", required=True, help="WAV sample in this folder (e.g. field_ops.wav)")
    args = parser.parse_args()

    audio = Path(args.audio)
    if not audio.is_absolute():
        audio = SCRIPT_DIR / audio
    if not audio.exists():
        print(f"error: file not found: {audio}", file=sys.stderr)
        raise SystemExit(2)

    domain = audio.stem
    if domain not in VALID_DOMAINS:
        print(
            f"error: unknown sample '{audio.name}'. "
            f"Use one of: {', '.join(f'{d}.wav' for d in VALID_DOMAINS)}",
            file=sys.stderr,
        )
        raise SystemExit(2)

    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        print("error: set CARTESIA_API_KEY before running.", file=sys.stderr)
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

    transcript_path = audio.with_name(f"{audio.stem}-transcribed.txt")
    transcript_path.write_text(transcript + "\n")

    print(json.dumps({
        "audio": audio.name,
        "domain": domain,
        "transcript": transcript,
        "transcript_file": transcript_path.name,
    }, indent=2))


if __name__ == "__main__":
    main()
