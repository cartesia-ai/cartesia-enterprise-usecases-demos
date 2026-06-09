"""Multilingual training audio with Cartesia Sonic-3.5 TTS.

Turn one training script into natural speech in multiple languages, each voiced
by a voice native to it, one generation per language. No voice actor, no studio:
change the script and regenerate instead of re-recording per language. This is
model-only (Sonic-3.5 TTS); it produces the spoken material, it does not grade a
learner's reply.

Setup:
    uv add cartesia
    export CARTESIA_API_KEY="your-cartesia-api-key"

Run:
    uv run python examples/02_multilingual_training_practice/02_multilingual_training_practice.py --language es
    # also: --language en | --language fr, or pass your own --text

Docs:
    Sonic-3.5 overview:  https://docs.cartesia.ai/build-with-cartesia/tts-models/latest
    TTS API ref:         https://docs.cartesia.ai/api-reference/tts/bytes
"""

import argparse
import json
import os
import sys
from pathlib import Path

from cartesia import Cartesia

SCRIPT_DIR = Path(__file__).parent

# A voice native to each language. Cross-lingual (one voice speaking several
# languages) isn't generally available in Sonic-3.5 yet, so each language uses its
# own native voice. Override any of these with the CARTESIA_VOICE_ID env var.
VOICE_IDS = {
    "en": "47c38ca4-5f35-497b-b1a3-415245fb35e1",  # Daniel - Modern Assistant
    "es": "9d8c6b2e-0a23-4a15-ae1b-121d5b5af417",  # Nuria - Trusted Advisor (Castilian)
    "fr": "7c58f4a4-a72c-42fa-a503-41b9408820f3",  # Inès - Poised Communicator (Parisian)
}

# Built-in enablement scenario: a customer-greeting drill a rep can listen to and
# repeat. The same line in each language, voiced by that language's native voice.
SCENARIOS = {
    "en": "Welcome to the team. Let's practice greeting a customer with a positive energy: 'Hi Daniela! thanks for calling. How can I help you today?'",
    "es": "Bienvenido al equipo. Practiquemos cómo saludar a un cliente con energía positiva: '¡Hola Daniela! Gracias por llamar. ¿En qué puedo ayudarle hoy?'",
    "fr": "Bienvenue dans l'équipe. Entraînons-nous à accueillir un client avec une énergie positive : 'Bonjour Danielle! Merci de votre appel. Comment puis-je vous aider aujourd'hui ?'",
}


def synthesize_speech(api_key: str, text: str, language: str, voice_id: str, output_path: Path) -> None:
    client = Cartesia(api_key=api_key)

    resp = client.tts.generate(
        model_id="sonic-3.5",
        transcript=text,
        voice={"mode": "id", "id": voice_id},
        language=language,
        output_format={"container": "wav", "encoding": "pcm_s16le", "sample_rate": 44100},
    )
    resp.write_to_file(str(output_path))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate spoken training audio with Sonic-3.5 TTS."
    )
    parser.add_argument("--language", default="en", help="BCP-47 language code (default: en)")
    parser.add_argument("--text", default=None, help="Custom text to speak; uses built-in scenario if omitted")
    parser.add_argument("--output", default=None, help="Output WAV filename (default: training_<language>.wav, or output_<language>.wav with --text)")
    args = parser.parse_args()

    api_key = os.environ.get("CARTESIA_API_KEY")
    if not api_key:
        sys.exit("Error: set CARTESIA_API_KEY environment variable.")

    text = args.text or SCENARIOS.get(args.language)
    if not text:
        sys.exit(f"Error: no built-in scenario for '{args.language}'. Provide --text explicitly.")

    voice_id = os.environ.get("CARTESIA_VOICE_ID") or VOICE_IDS.get(args.language)
    if not voice_id:
        sys.exit(f"Error: no built-in voice for '{args.language}'. Set CARTESIA_VOICE_ID, or use en, es, or fr.")

    # Custom text writes output_<language>.wav so it never overwrites the bundled training_<language>.wav samples.
    default_name = f"output_{args.language}.wav" if args.text else f"training_{args.language}.wav"
    output_name = args.output or default_name
    if not output_name.endswith(".wav"):
        output_name += ".wav"
    output_path = SCRIPT_DIR / output_name

    synthesize_speech(api_key, text, args.language, voice_id, output_path)

    result = {
        "text": text,
        "language": args.language,
        "voice_id": voice_id,
        "output_file": str(output_path),
        "model": "sonic-3.5",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
