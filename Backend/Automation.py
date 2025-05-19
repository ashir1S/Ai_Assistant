"""
automation.py
Core command-dispatch module for the Voice AI Assistant.
Handles opening apps, performing web searches, content generation, media playback,
and system-level controls via an async task scheduler.
"""

# --- Imports ---
# Standard library
import os
import sys
import subprocess
import asyncio
from pathlib import Path
import logging

# Third-party
from AppOpener import close, open as appopen
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from rich import print
from groq import Groq
from pywhatkit import search, playonyt
import requests
import keyboard

# Local alias for browser
from webbrowser import open as webopen

# --- Helper for PyInstaller path resolution ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load environment variables from the correct path
load_dotenv(dotenv_path=resource_path('.env'))

# Get your keys using os.getenv
GroqAPIKey = os.getenv("GroqAPIKey")
Username = os.getenv("Username", "Assistant")

# Ensure data directory exists for content files
data_dir = Path(resource_path("Data"))
data_dir.mkdir(parents=True, exist_ok=True)

# CSS classes for HTML parsing (Google search fallback)
CLASSES = [
    "zCubwf", "hgKElc", "LTKOO sY7ric", "Z0LcW", "gsrt vk_bk FzvWSb YwPhnf",
    "pclqee", "tw-Data-text tw-text-small tw-ta", "IZ67rdc", "O5uR6d LTKOO",
    "vlzY6d", "webanswers-webanswers_table__webanswers-table", "dDoNo ikb4Bb gsrt",
    "sXLaOe", "LWkFke", "VQF4g", "qv3Wpe", "Kno-rdesc", "SPZz6b"
]
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/100.0.4896.75 Safari/537.36'
)

# Initialize AI client
if not GroqAPIKey:
    raise ValueError("Groq API key not found in environment variables")
groq_client = Groq(api_key=GroqAPIKey)

# Chatbot context
messages = []
system_message = {
    "role": "system",
    "content": f"Hello, I am {Username}. You are a content writer."
}

# --- Helper Functions ---

def generate_and_save_content(topic: str) -> str:
    """
    Generate AI content for a given topic, save to a text file, and open in Notepad.
    Returns a human-readable status message.
    """
    clean_topic = topic.replace("Content ", "").strip()
    prompt = clean_topic

    # Prepare messages
    messages.append({"role": "user", "content": prompt})
    response_chunks = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[system_message] + messages,
        max_tokens=2048,
        temperature=0.7,
        top_p=1,
        stream=True
    )

    # Collect answer
    answer = ""
    for chunk in response_chunks:
        delta = chunk.choices[0].delta.content
        if delta:
            answer += delta

    answer = answer.replace("</s>", "").strip()
    messages.append({"role": "assistant", "content": answer})

    # Write to file
    filename = data_dir / f"{clean_topic.lower().replace(' ', '')}.txt"
    filename.write_text(answer, encoding="utf-8")
    subprocess.Popen(["notepad.exe", str(filename)])

    return f"Content generated and saved to {filename.name}."


def perform_google_search(query: str) -> str:
    """
    Perform a pywhatkit search (opens browser). Returns status.
    """
    try:
        search(query)
        return f"Searched Google for '{query}'."
    except Exception as e:
        logging.error(f"GoogleSearch error: {e}")
        return "Failed to perform Google search."


def youtube_search(query: str) -> str:
    """
    Open YouTube search results in the default browser.
    """
    url = f"https://www.youtube.com/results?search_query={query}"
    webopen(url)
    return f"Opened YouTube search for '{query}'."


def play_youtube_video(query: str) -> str:
    """
    Play a YouTube video via pywhatkit.
    """
    try:
        playonyt(query)
        return f"Playing YouTube video for '{query}'."
    except Exception as e:
        logging.error(f"PlayYoutube error: {e}")
        return "Failed to play YouTube video."


def open_app(app_name: str) -> str:
    """
    Open an application by name; fallback to Google-search link extraction.
    """
    try:
        appopen(app_name, match_closest=True, output=True, throw_error=True)
        return f"Opened application '{app_name}'."
    except Exception:
        # Fallback via web search and link extraction
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(f"https://www.google.com/search?q={app_name}", headers=headers)
        if resp.status_code != 200:
            return f"Could not find '{app_name}' online."

        soup = BeautifulSoup(resp.text, 'html.parser')
        link = soup.find('a', href=True)
        if link:
            webopen(link['href'])
            return f"Opened web link for '{app_name}'."
        return f"No link found for '{app_name}'."


def close_app(app_name: str) -> str:
    """
    Close an application by name.
    """
    if "chrome" in app_name.lower():
        return "Cannot close Chrome via this command."
    try:
        close(app_name, match_closest=True, output=True, throw_error=True)
        return f"Closed application '{app_name}'."
    except Exception as e:
        logging.error(f"CloseApp error: {e}")
        return f"Failed to close '{app_name}'."


def handle_system_command(command: str) -> str:
    """
    Handle mute/unmute/volume up/down.
    """
    mapping = {
        "mute": lambda: keyboard.press_and_release("volume mute"),
        "unmute": lambda: keyboard.press_and_release("volume mute"),
        "volume up": lambda: keyboard.press_and_release("volume up"),
        "volume down": lambda: keyboard.press_and_release("volume down"),
    }
    action = mapping.get(command)
    if action:
        action()
        return f"Executed system command '{command}'."
    return f"Unknown system command '{command}'."

# --- Async Command Translation & Execution ---

async def translate_and_execute(commands: list[str]) -> list[str]:
    """
    Convert text commands into async tasks, run them concurrently, and return status messages.
    """
    tasks = []
    for cmd in commands:
        cmd_lower = cmd.strip().lower()
        if cmd_lower.startswith("open "):
            tasks.append(asyncio.to_thread(open_app, cmd_lower.removeprefix("open ")))
        elif cmd_lower.startswith("close "):
            tasks.append(asyncio.to_thread(close_app, cmd_lower.removeprefix("close ")))
        elif cmd_lower.startswith("play "):
            tasks.append(asyncio.to_thread(play_youtube_video, cmd_lower.removeprefix("play ")))
        elif cmd_lower.startswith("content "):
            tasks.append(asyncio.to_thread(generate_and_save_content, cmd_lower.removeprefix("content ")))
        elif cmd_lower.startswith("google search "):
            tasks.append(asyncio.to_thread(perform_google_search, cmd_lower.removeprefix("google search ")))
        elif cmd_lower.startswith("youtube search "):
            tasks.append(asyncio.to_thread(youtube_search, cmd_lower.removeprefix("youtube search ")))
        elif cmd_lower.startswith("system "):
            tasks.append(asyncio.to_thread(handle_system_command, cmd_lower.removeprefix("system ")))
        else:
            logging.warning(f"Unrecognized command: '{cmd}'")
            tasks.append(asyncio.to_thread(lambda: f"No handler for '{cmd}'"))

    # Run all tasks and capture exceptions per-task
    results = await asyncio.gather(*tasks, return_exceptions=True)
    statuses = []
    for res in results:
        if isinstance(res, Exception):
            logging.error(f"Task error: {res}")
            statuses.append("An error occurred during command execution.")
        else:
            statuses.append(res)
    return statuses

async def automate(commands: list[str]) -> list[str]:
    """
    High-level entry point: translate and execute commands, then return spoken responses.
    """
    responses = await translate_and_execute(commands)
    return responses

# --- Testing Harness ---
# if __name__ == "__main__":
#     # Example commands to test each feature of automation.py
#     # NOTE: Avoid using "close notepad" here if your .txt handler opens VS Code
#     test_commands = [
#         "open calc",              # Opens Calculator
#         "content Test Content",   # Generates dummy content
#         "google search OpenAI",   # Performs a Google search
#         "youtube search ChatGPT tutorial",  # Opens YouTube search
#         "play Rick Astley Never Gonna Give You Up",  # Plays a video
#         "system mute",            # Mutes volume
#         # "close notepad"         # Uncomment to test closing Notepad (may close VS Code on some systems)
#     ]
#
#     # Execute automation and print status messages
#     import asyncio
#     results = asyncio.run(automate(test_commands))
#     for status in results:
#         print(status)
