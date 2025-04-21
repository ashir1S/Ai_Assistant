from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

GroqAPIKey = os.environ.get("GroqAPIKey")

client = Groq(api_key=GroqAPIKey) if GroqAPIKey else None# Import the Groq library to use its API.
if client is None:
    print("Error: GROQ_API_KEY not found in environment variables.")
from json import load, dump  # Functions to read and write JSON files.
import datetime  # For real-time date and time info.
# To read environment variables from a .env file.
from dotenv import dotenv_values
import subprocess  # To execute system commands.
import re  # For regex-based splitting.
from .Model import FirstLayerDMM  # Import classification logic from model.py.
import os  # For os.startfile()
import json  # For loading app mappings.
from fuzzywuzzy import process  # For fuzzy matching

# Windows flag to create no window when using subprocess.Popen.
CREATE_NO_WINDOW = 0x08000000

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
# GroqAPIKey = env_vars.get("GroqAPIKey")

# Initialize the Groq client using the provided API key.
# client = Groq(api_key=GroqAPIKey)

# Global path for the chat log file.
CHAT_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Data", "ChatLog.json"
)
CHAT_LOG_FILE = os.path.abspath(CHAT_LOG_FILE)


# Function to load app mappings from the project root.


def load_app_mappings():
    try:
        # Get the root directory (one level up from the Backend folder).
        root_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), ".."))
        mapping_path = os.path.join(root_dir, "app_mappings.json")
        with open(mapping_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading app mappings: {e}")
        return {}


# Load app mappings.
APP_MAPPINGS = load_app_mappings()


def load_chat_log():
    try:
        with open(CHAT_LOG_FILE, "r") as f:
            return load(f)
    except FileNotFoundError:
        with open(CHAT_LOG_FILE, "w") as f:
            dump([], f)
        return []
    except Exception as e:
        print(f"Error loading chat log: {e}")
        return []


def save_chat_log(log):
    try:
        with open(CHAT_LOG_FILE, "w") as f:
            dump(log, f, indent=4)
    except Exception as e:
        print(f"Error saving chat log: {e}")


# Updated System message.
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which also has real-time up-to-date information from the internet.
*** Do not tell time until I ask, do not talk too much, just answer the question.***
*** Reply in only English, even if the question is in Hindi, reply in English.***
*** Do not provide notes in the output, just answer the question and never mention your training data. ***
"""

SystemChatBot = [{"role": "system", "content": System}]


def RealtimeInformation():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    data = f"Please use this real-time information if needed,\n"
    data += f"Day: {day}\nDate: {date}\nMonth: {month}\nYear: {year}\n"
    return data


def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)


def find_executable(app_name):
    """
    Attempt to find the executable path using Windows 'where' command.
    Returns the first found executable if available.
    """
    try:
        result = subprocess.run(["where", app_name],
                                shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.splitlines()[0]
    except Exception as e:
        print(f"Error in find_executable: {e}")
    return app_name


def fuzzy_map_app(app_name):
    """
    Use fuzzy matching to map a misspelled app name to a key in APP_MAPPINGS.
    Returns the mapped executable if a good match is found, otherwise None.
    """
    keys = list(APP_MAPPINGS.keys())
    match, score = process.extractOne(app_name, keys)
    if score >= 80:
        return APP_MAPPINGS[match]
    return None


def extract_app_name(command, prefix):
    """
    Extract the app name from a command.
    Supports both "open ( app_name )" and "open app_name" formats.
    """
    remainder = command[len(prefix):].strip()
    if remainder.startswith("(") and remainder.endswith(")"):
        return remainder[1:-1].strip().lower()
    else:
        return remainder.lower()


def execute_command(command):
    """
    Execute system commands based on classification (open, close, play).
    Uses APP_MAPPINGS first; if not available, applies fuzzy matching, then auto-detects via 'where'.
    """
    if "(" not in command or ")" not in command:
        print("Command format invalid.")
        return

    if command.startswith("open"):
        try:
            app_name = extract_app_name(command, "open")
            mapped_app = APP_MAPPINGS.get(app_name, None)
            if not mapped_app:
                mapped_app = fuzzy_map_app(app_name)
            if not mapped_app:
                mapped_app = find_executable(app_name)
            print(f"Executing command: Opening {mapped_app}...")
            try:
                os.startfile(mapped_app)
            except Exception as e:
                print(f"os.startfile() failed: {e}, falling back to Popen...")
                subprocess.Popen(mapped_app, shell=True,
                                 creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error executing open command: {e}")
    elif command.startswith("close"):
        try:
            app_name = extract_app_name(command, "close")
            mapped_app = APP_MAPPINGS.get(app_name, None)
            if not mapped_app:
                mapped_app = fuzzy_map_app(app_name)
            if not mapped_app:
                mapped_app = find_executable(app_name)
            print(f"Executing command: Closing {mapped_app}...")
            subprocess.run(
                ["taskkill", "/IM", f"{mapped_app}.exe", "/F"], shell=True)
        except Exception as e:
            print(f"Error executing close command: {e}")
    elif command.startswith("play"):
        try:
            app_name = extract_app_name(command, "play")
            mapped_app = APP_MAPPINGS.get(app_name, None)
            if not mapped_app:
                mapped_app = fuzzy_map_app(app_name)
            if not mapped_app:
                mapped_app = find_executable(app_name)
            print(f"Executing command: Playing {mapped_app}...")
            try:
                os.startfile(mapped_app)
            except Exception as e:
                print(f"os.startfile() failed: {e}, falling back to Popen...")
                subprocess.Popen(mapped_app, shell=True,
                                 creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Error executing play command: {e}")
    else:
        print("Command not recognized by router.")


def command_router(query):
    """
    Use model.py classification to determine if the query is a system command.
    If so, execute it; otherwise, return None.
    """
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
            messages=SystemChatBot +
            [{"role": "system", "content": RealtimeInformation()}] + messages,
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
        # First, check if it's a system command.
        cmd_result = command_router(user_input)
        if cmd_result:
            print(cmd_result)
        else:
            response = ChatBot(user_input)
            print(response)
