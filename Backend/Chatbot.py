import os
import sys
import subprocess
import datetime
import json
from dotenv import load_dotenv
from fuzzywuzzy import process
from groq import Groq
from .Model import FirstLayerDMM

# --- Helper for PyInstaller path resolution ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# --- Load environment variables ---
load_dotenv(dotenv_path=resource_path('.env'))
Username = os.getenv("Username")
Assistantname = os.getenv("Assistantname")
GroqAPIKey = os.getenv("GroqAPIKey")

if not GroqAPIKey:
    print("Error: GroqAPIKey not found in environment variables.")
    sys.exit(1)

client = Groq(api_key=GroqAPIKey)

# --- Chat log file path ---
chatlog_path = resource_path(os.path.join("Data", "ChatLog.json"))
data_dir = os.path.dirname(chatlog_path)
os.makedirs(data_dir, exist_ok=True)

def load_chat_log():
    try:
        with open(chatlog_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(chatlog_path, "w") as f:
            json.dump([], f)
        return []
    except Exception as e:
        print(f"Error loading chat log: {e}")
        return []

def save_chat_log(log):
    try:
        with open(chatlog_path, "w") as f:
            json.dump(log, f, indent=4)
    except Exception as e:
        print(f"Error saving chat log: {e}")

# --- System message ---
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""
SystemChatBot = [{"role": "system", "content": System}]

def RealtimeInformation():
    now = datetime.datetime.now()
    return (
        f"Please use this real-time information if needed,\n"
        f"Day: {now.strftime('%A')}\n"
        f"Date: {now.strftime('%d')}\n"
        f"Month: {now.strftime('%B')}\n"
        f"Year: {now.strftime('%Y')}\n"
    )

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

# --- App mappings ---
def load_app_mappings():
    try:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        mapping_path = os.path.join(root_dir, "app_mappings.json")
        with open(mapping_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading app mappings: {e}")
        return {}

APP_MAPPINGS = load_app_mappings()

def find_executable(app_name):
    try:
        result = subprocess.run(["where", app_name], shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()[0]
    except Exception as e:
        print(f"Error in find_executable: {e}")
    return app_name

def fuzzy_map_app(app_name):
    keys = list(APP_MAPPINGS.keys())
    match, score = process.extractOne(app_name, keys)
    if score >= 80:
        return APP_MAPPINGS[match]
    return None

def extract_app_name(command, prefix):
    remainder = command[len(prefix):].strip()
    if remainder.startswith("(") and remainder.endswith(")"):
        return remainder[1:-1].strip().lower()
    else:
        return remainder.lower()

CREATE_NO_WINDOW = 0x08000000

def execute_command(command):
    if "(" not in command or ")" not in command:
        print("Command format invalid.")
        return

    if command.startswith("open"):
        try:
            app_name = extract_app_name(command, "open")
            mapped_app = APP_MAPPINGS.get(app_name) or fuzzy_map_app(app_name) or find_executable(app_name)
            print(f"Executing command: Opening {mapped_app}...")
            try:
                os.startfile(mapped_app)
            except Exception as e:
                print(f"os.startfile() failed: {e}, falling back to Popen...")
                subprocess.Popen(mapped_app, shell=True, creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error executing open command: {e}")
    elif command.startswith("close"):
        try:
            app_name = extract_app_name(command, "close")
            mapped_app = APP_MAPPINGS.get(app_name) or fuzzy_map_app(app_name) or find_executable(app_name)
            print(f"Executing command: Closing {mapped_app}...")
            subprocess.run(["taskkill", "/IM", f"{mapped_app}.exe", "/F"], shell=True)
        except Exception as e:
            print(f"Error executing close command: {e}")
    elif command.startswith("play"):
        try:
            app_name = extract_app_name(command, "play")
            mapped_app = APP_MAPPINGS.get(app_name) or fuzzy_map_app(app_name) or find_executable(app_name)
            print(f"Executing command: Playing {mapped_app}...")
            try:
                os.startfile(mapped_app)
            except Exception as e:
                print(f"os.startfile() failed: {e}, falling back to Popen...")
                subprocess.Popen(mapped_app, shell=True, creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error executing play command: {e}")
    else:
        print("Command not recognized by router.")

def command_router(query):
    classification = FirstLayerDMM(query)
    if classification and (classification[0].startswith("open") or
                           classification[0].startswith("close") or
                           classification[0].startswith("play")):
        execute_command(classification[0])
        return f"Executed command: {classification[0]}"
    else:
        return None

def ChatBot(Query):
    try:
        messages = load_chat_log()
        messages.append({"role": "user", "content": Query})
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=SystemChatBot + [{"role": "system", "content": RealtimeInformation()}] + messages,
            max_tokens=1024,
            temperature=0.7,
            top_p=1,
            stream=True,
            stop=None
        )
        Answer = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content
        Answer = Answer.replace("<|%", "")
        messages.append({"role": "assistant", "content": Answer})
        save_chat_log(messages)
        return AnswerModifier(Answer)
    except Exception as e:
        print(f"Error: {e}")
        save_chat_log([])
        return "An error occurred while processing your query."

if __name__ == "__main__":
    while True:
        user_input = input("\nEnter Your Question: ").strip()
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Goodbye!")
            break
        cmd_result = command_router(user_input)
        if cmd_result:
            print(cmd_result)
        else:
            response = ChatBot(user_input)
            print(response)
