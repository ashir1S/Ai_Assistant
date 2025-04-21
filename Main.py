import os
import json
import subprocess
import threading
from asyncio import run as asyncio_run
from time import sleep
from dotenv import load_dotenv, dotenv_values
from Frontend.GUI import (
    GraphicalUserInterface, SetAssistantStatus, ShowTextToScreen,
    TempDirectoryPath, SetMicrophoneStatus, AnswerModifier,
    QueryModifier, GetMicrophoneStatus, GetAssistantStatus
)
from Backend.Chatbot import ChatBot
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import automate as Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.TextToSpeech import text_to_speech as TextToSpeech
import re
import webbrowser

# Load environment variables
load_dotenv()
env_vars = dotenv_values(".env")
USERNAME = env_vars.get("Username", "User")
ASSISTANT_NAME = env_vars.get("Assistantname", "Assistant")
DEFAULT_MESSAGE = (
    f"{USERNAME}: Hello {ASSISTANT_NAME}, How are you?\n"
    f"{ASSISTANT_NAME}: Welcome {USERNAME}. I am doing well. How may I help you?"
)

# Globals and paths
SUBPROCESS_LIST = []
FUNCTIONS = ["open", "close", "play", "system", "content", "google search", "youtube search"]
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Add at the top
CHATLOG_PATH = os.path.join(BASE_DIR, "Data", "ChatLog.json")


# Initialization helpers

def ensure_chatlog_exists():
    if not os.path.exists(CHATLOG_PATH):
        os.makedirs(os.path.dirname(CHATLOG_PATH), exist_ok=True)
        with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def show_default_chat_if_no_chats():
    ensure_chatlog_exists()
    with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if len(content) < 5:
        db_path = TempDirectoryPath("Database.data")
        resp_path = TempDirectoryPath("Responses.data")
        with open(db_path, "w", encoding="utf-8"): pass
        with open(resp_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_MESSAGE)


def read_chatlog():
    ensure_chatlog_exists()
    with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def integrate_chatlog():
    messages = read_chatlog()
    formatted = []
    for entry in messages:
        role = entry.get("role")
        text = entry.get("content", "")
        if role == "user":
            formatted.append(f"{USERNAME}: {text}")
        elif role == "assistant":
            formatted.append(f"{ASSISTANT_NAME}: {text}")
    merged = "\n".join(formatted)
    db_path = TempDirectoryPath("Database.data")
    with open(db_path, "w", encoding="utf-8") as f:
        f.write(AnswerModifier(merged))


def show_chats_on_gui():
    db_path = TempDirectoryPath("Database.data")
    resp_path = TempDirectoryPath("Responses.data")
    with open(db_path, "r", encoding="utf-8") as f:
        data = f.read()
    if data:
        with open(resp_path, "w", encoding="utf-8") as f:
            f.write(data)


def initial_setup():
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    show_default_chat_if_no_chats()
    integrate_chatlog()
    show_chats_on_gui()

# Handlers for different command types

def handle_general(query):
    SetAssistantStatus("Thinking...")
    response = ChatBot(QueryModifier(query))
    ShowTextToScreen(f"{ASSISTANT_NAME}: {response}")
    SetAssistantStatus("Answering...")
    TextToSpeech(response)


def handle_realtime(query):
    SetAssistantStatus("Searching...")
    response = RealtimeSearchEngine(QueryModifier(query))
    ShowTextToScreen(f"{ASSISTANT_NAME}: {response}")
    SetAssistantStatus("Answering...")
    TextToSpeech(response)

def handle_image_generation(query):
    base_dir = os.path.dirname(os.path.abspath(__file__))  # This gets the actual path of Main.py
    file_path = os.path.join(base_dir, "Frontend", "Files", "imageGeneration.data")
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Ensure the directory exists
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{query},True")

    try:
        proc = subprocess.Popen(
            ["python", os.path.join(base_dir, "Backend", "ImageGeneration.py")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        SUBPROCESS_LIST.append(proc)
    except Exception as e:
        print(f"Error starting ImageGeneration.py: {e}")



# Sanitize automation commands

def sanitize_automation_cmd(cmd):
    parts = cmd.split(None, 1)
    func = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    arg_clean = re.sub(r"[\(\)\.\s]+", " ", arg).strip()
    return func, arg_clean

# Main interaction loop

def main_execution():
    SetAssistantStatus("Listening...")
    user_query = SpeechRecognition()
    ShowTextToScreen(f"{USERNAME}: {user_query}")
    SetAssistantStatus("Thinking...")

    decisions = FirstLayerDMM(user_query)
    print(f"Decision: {decisions}")

    # Automation tasks: handle open vs others
    for d in decisions:
        for func in FUNCTIONS:
            if d.lower().startswith(func):
                func_key, arg = sanitize_automation_cmd(d)
                if func_key == "open" and arg:
                    # URL open if arg has dot or https prefix
                    if "." in arg or arg.lower().startswith("http"):
                        url = arg if arg.lower().startswith("http") else f"https://{arg}"
                        webbrowser.open(url)
                        
                    else:
                        # Try system open via Automation; catch failure
                        try:
                            asyncio_run(Automation([d]))
                        except Exception:
                            ShowTextToScreen(f"{ASSISTANT_NAME}: Unable to open '{arg}'.")
                else:
                    # Non-open automation via Automation
                    try:
                        asyncio_run(Automation([d]))
                    except Exception:
                        ShowTextToScreen(f"{ASSISTANT_NAME}: Error executing '{d}'.")

    # Image generation
    image_cmds = [d for d in decisions if d.startswith("generate ")]
    if image_cmds:
        handle_image_generation(image_cmds[0].replace("generate ", ""))

    # Realtime vs General vs Exit
    realtime_cmds = [d for d in decisions if d.startswith("realtime ")]
    general_cmds = [d for d in decisions if d.startswith("general ")]
    exit_cmds = [d for d in decisions if d == "Exit"]

    if realtime_cmds:
        merged = " and ".join(cmd.replace("realtime ", "") for cmd in realtime_cmds)
        handle_realtime(merged)
    elif general_cmds:
        handle_general(general_cmds[0].replace("general ", ""))
    elif exit_cmds:
        handle_general("Okay, Bye!")
        os._exit(0)

# Thread to monitor microphone status

def microphone_thread():
    while True:
        if GetMicrophoneStatus() == "True":
            main_execution()
        else:
            status = GetAssistantStatus()
            if "Available" not in status:
                SetAssistantStatus("Available...")
            sleep(0.1)

# Startup

def run_app():
    initial_setup()
    listener = threading.Thread(target=microphone_thread, daemon=True)
    listener.start()
    GraphicalUserInterface()

if __name__ == "__main__":
    run_app()