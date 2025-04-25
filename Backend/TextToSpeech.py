import logging
import random
import asyncio
from pathlib import Path
from typing import Callable
import pygame
import edge_tts
import keyboard  # <- ADDED
from dotenv import dotenv_values

# ─── CONFIG & LOGGING ─────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ─── PATH SETUP ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_FILE = DATA_DIR / "speech.mp3"

# ─── VOICE SETUP ──────────────────────────────────────────────────────────────
DEFAULT_VOICE = "en-US-JennyNeural"
logging.info(f"Using TTS voice: {DEFAULT_VOICE}")

# ─── PREDEFINED RESPONSES ─────────────────────────────────────────────────────
RESPONSES = [
    "The rest of the result has been printed to the chat screen, kindly check it out sir.",
    "The rest of the text is now on the chat screen, sir, please check it.",
    "You can see the rest of the text on the chat screen, sir.",
    "The remaining part of the text is now on the chat screen, sir.",
    "Sir, you'll find more text on the chat screen for you to see.",
    "The rest of the answer is now on the chat screen, sir.",
    "Sir, please look at the chat screen, the rest of the answer is there.",
    "You'll find the complete answer on the chat screen, sir.",
    "The next part of the text is on the chat screen, sir.",
    "Sir, please check the chat screen for more information.",
    "There's more text on the chat screen for you, sir.",
    "Sir, take a look at the chat screen for additional text.",
    "You'll find more to read on the chat screen, sir.",
    "Sir, check the chat screen for the rest of the text.",
    "The chat screen has the rest of the text, sir.",
    "There's more to see on the chat screen, sir, please look.",
    "Sir, the chat screen holds the continuation of the text.",
    "You'll find the complete answer on the chat screen, kindly check it out sir.",
    "Please review the chat screen for the rest of the text, sir.",
    "Sir, look at the chat screen for the complete answer."
]

# ─── CORE FUNCTIONS ────────────────────────────────────────────────────────────

async def text_to_audio_file(text: str) -> bool:
    try:
        if AUDIO_FILE.exists():
            AUDIO_FILE.unlink()
        logging.info(f"Generating TTS audio (sample): {text[:20]!r}")
        communicator = edge_tts.Communicate(text=text, voice=DEFAULT_VOICE)
        await communicator.save(str(AUDIO_FILE))
        return True
    except Exception:
        logging.exception("Failed to generate TTS audio.")
        return False


def tts(text: str, callback: Callable[[bool], bool] = lambda _: True) -> bool:
    if not asyncio.run(text_to_audio_file(text)):
        return False

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(str(AUDIO_FILE))
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            if keyboard.is_pressed("s"):  # PRESS 's' TO STOP
                logging.info("Speech interrupted by user (pressed 's')")
                pygame.mixer.music.stop()
                break
            if not callback(True):
                pygame.mixer.music.stop()
                break
            pygame.time.Clock().tick(10)

        return True

    except Exception:
        logging.exception("Playback failed.")
        return False

    finally:
        try:
            callback(False)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            logging.exception("Cleanup failed.")


def text_to_speech(text: str, callback: Callable[[bool], bool] = lambda _: True) -> None:
    """
    If the user says "in detail" or "complete", read all.
    Otherwise, give short summary + ending prompt.
    """
    lowered = text.lower()
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    detailed_trigger = any(kw in lowered for kw in ["in detail", "complete", "fully", "elaborate"])

    if detailed_trigger or (len(sentences) <= 3 or len(text) < 250):
        tts(text, callback)
    else:
        snippet = '. '.join(sentences[:2]) + '. ' + random.choice(RESPONSES)
        tts(snippet, callback)
        
    # def text_to_speech(text: str, callback: Callable[[bool], bool] = lambda _: True) -> None: // for full text
    # """
    # Reads the full text aloud until user presses 's' to stop.
    # """
    # tts(text, callback)
    


# ─── MODULE TEST ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    while True:
        user_input = input("Enter text: ")
        text_to_speech(user_input)
