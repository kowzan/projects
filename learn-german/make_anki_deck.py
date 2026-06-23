from pathlib import Path
import hashlib
import html
import json
import time

import genanki
from deep_translator import GoogleTranslator
from gtts import gTTS


# =========================
# Configuration
# =========================

INPUT_FILE = Path("german_sentences.txt")
OUTPUT_APKG = "german_sentences_pl_de_audio.apkg"

DECK_NAME = "German Sentences PL-DE with Audio"

AUDIO_DIR = Path("anki_audio")
CACHE_FILE = Path("translation_cache_de_pl.json")

# Generate once and keep it constant.
# You can change it, but do not change it on every run
# if you want to update the same deck in Anki.
DECK_ID = 2059400110
MODEL_ID = 1607392319


# =========================
# Helper functions
# =========================

def read_sentences(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    sentences = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue
            if text.startswith("#"):
                continue
            sentences.append(text)

    return sentences


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def load_cache(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(path: Path, cache: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def translate_de_to_pl(text: str, translator: GoogleTranslator, cache: dict) -> str:
    if text in cache:
        return cache[text]

    translated = translator.translate(text)
    cache[text] = translated

    # Small delay to avoid sending requests too aggressively.
    time.sleep(0.3)

    return translated


def create_tts_mp3(german_text: str, audio_dir: Path) -> Path:
    audio_dir.mkdir(exist_ok=True)

    filename = f"de_{short_hash(german_text)}.mp3"
    audio_path = audio_dir / filename

    if audio_path.exists():
        return audio_path

    tts = gTTS(text=german_text, lang="de")
    tts.save(str(audio_path))

    time.sleep(0.3)

    return audio_path


# =========================
# Anki card model
# =========================

model = genanki.Model(
    MODEL_ID,
    "PL front - DE back with audio",
    fields=[
        {"name": "Polish"},
        {"name": "German"},
        {"name": "Audio"},
    ],
    templates=[
        {
            "name": "Polish to German",
            "qfmt": """
                <div class="label">Polish</div>
                <div class="front-text">{{Polish}}</div>
            """,
            "afmt": """
                {{FrontSide}}

                <hr id="answer">

                <div class="label">German</div>
                <div class="back-text">{{German}}</div>

                <div class="audio">
                    {{Audio}}
                </div>
            """,
        }
    ],
    css="""
        .card {
            font-family: Arial, sans-serif;
            font-size: 24px;
            text-align: center;
            color: #222;
            background-color: #fff;
            line-height: 1.5;
        }

        .label {
            font-size: 14px;
            color: #777;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }

        .front-text {
            font-size: 28px;
            font-weight: 600;
        }

        .back-text {
            font-size: 30px;
            font-weight: 600;
            color: #111;
            margin-bottom: 18px;
        }

        .audio {
            margin-top: 16px;
        }
    """,
)


# =========================
# Main logic
# =========================

def main() -> None:
    sentences = read_sentences(INPUT_FILE)

    if not sentences:
        raise ValueError("Input file does not contain any sentences.")

    translator = GoogleTranslator(source="de", target="pl")
    cache = load_cache(CACHE_FILE)

    deck = genanki.Deck(
        DECK_ID,
        DECK_NAME,
    )

    media_files = []

    for idx, german_sentence in enumerate(sentences, start=1):
        print(f"[{idx}/{len(sentences)}] {german_sentence}")

        polish_translation = translate_de_to_pl(
            german_sentence,
            translator,
            cache,
        )

        audio_path = create_tts_mp3(
            german_sentence,
            AUDIO_DIR,
        )

        media_files.append(str(audio_path))

        audio_field = f"[sound:{audio_path.name}]"

        note = genanki.Note(
            model=model,
            fields=[
                html.escape(polish_translation),
                html.escape(german_sentence),
                audio_field,
            ],
            guid=genanki.guid_for(german_sentence),
        )

        deck.add_note(note)

    save_cache(CACHE_FILE, cache)

    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(OUTPUT_APKG)

    print()
    print(f"Done. File created: {OUTPUT_APKG}")
    print(f"Number of cards: {len(sentences)}")


if __name__ == "__main__":
    main()