import os
import sys
import logging
import random
import asyncio
from pathlib import Path
from typing import Callable
import pygame
import edge_tts
import keyboard
from dotenv import load_dotenv

# ─── PATH HANDLING ────────────────────────────────────────────────────────────
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# ─── CONFIG & LOGGING ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(resource_path('tts.log'))]
)

# Load environment variables from correct location
load_dotenv(dotenv_path=resource_path('.env'))

def resource_path(relative_path: str) -> Path:
    # Mimics the behavior of ROOT_DIR = Path(__file__).resolve().parent.parent
    root_dir = Path(__file__).resolve().parent.parent
    return root_dir / relative_path

# Now you can use it like this:
DATA_DIR = Path(resource_path("Data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_FILE = DATA_DIR / "speech.mp3"


# ─── PATH SETUP ────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "Data"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_FILE = DATA_DIR / "speech.mp3"

# ─── VOICE CONFIG ─────────────────────────────────────────────────────────────
DEFAULT_VOICE = os.getenv("TTS_VOICE", "en-US-JennyNeural")
logging.info(f"Initialized TTS with voice: {DEFAULT_VOICE}")

# ─── RESPONSE TEMPLATES ───────────────────────────────────────────────────────
RESPONSES = [
    "The rest of the result has been printed to the chat screen, kindly check it out sir.",
    # ... (keep your existing response templates)
]

# ─── CORE FUNCTIONS ───────────────────────────────────────────────────────────
async def generate_audio_file(text: str) -> bool:
    """Generate TTS audio file from text"""
    try:
        if AUDIO_FILE.exists():
            AUDIO_FILE.unlink()
            
        logging.info(f"Generating TTS audio: {text[:50]}...")
        communicator = edge_tts.Communicate(text=text, voice=DEFAULT_VOICE)
        await communicator.save(str(AUDIO_FILE))
        return True
    except Exception as e:
        logging.error(f"TTS generation failed: {str(e)}")
        return False

def play_audio_with_control(callback: Callable[[bool], bool] = lambda _: True) -> bool:
    """Play generated audio with playback control"""
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(str(AUDIO_FILE))
        pygame.mixer.music.play()
        logging.info("Playback started")

        while pygame.mixer.music.get_busy():
            if keyboard.is_pressed("s"):  # Stop on 's' key press
                logging.info("Playback stopped by user")
                pygame.mixer.music.stop()
                return False
            if not callback(True):
                pygame.mixer.music.stop()
                return False
            pygame.time.Clock().tick(10)
        return True
    except Exception as e:
        logging.error(f"Playback failed: {str(e)}")
        return False
    finally:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass

def text_to_speech(text: str, callback: Callable[[bool], bool] = lambda _: True) -> None:
    """Main TTS entry point with smart response handling"""
    try:
        if not asyncio.run(generate_audio_file(text)):
            return

        lowered = text.lower()
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        detailed_triggers = {"in detail", "complete", "fully", "elaborate"}

        if detailed_triggers.intersection(lowered.split()) or len(sentences) <= 3:
            play_audio_with_control(callback)
        else:
            snippet = '. '.join(sentences[:2]) + '. ' + random.choice(RESPONSES)
            if asyncio.run(generate_audio_file(snippet)):
                play_audio_with_control(callback)
    except Exception as e:
        logging.error(f"TTS processing failed: {str(e)}")

# ─── TEST HARNESS ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("TTS Module Test Mode")
    try:
        while True:
            text = input("Enter text to speak (or 'q' to quit): ").strip()
            if text.lower() in ('q', 'quit', 'exit'):
                break
            text_to_speech(text)
    except KeyboardInterrupt:
        logging.info("TTS test terminated")
