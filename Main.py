import os
import sys
import json
import subprocess
import threading
import re
import webbrowser
import traceback
import logging
import platform
from asyncio import run as asyncio_run
from time import sleep
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

# 1. Activate the virtual environment:  .\venv\Scripts\Activate

# 2. Run your script:  python -u "d:\AI\Assistant_ai\Main.py"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Attempt to import GUI components ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # If needed:
    # sys.path.insert(0, current_dir)
    # sys.path.insert(0, os.path.join(current_dir, "Frontend"))

    logging.info(f"Attempting GUI import. Current sys.path: {sys.path}")

    # Import the VARIABLE TEMP_DIR_PATH instead of the function TempDirectoryPath
    from Frontend.GUI import (
        graphical_user_interface, set_assistant_status, show_text_to_screen,
        TEMP_DIR_PATH, # <--- Corrected import
        set_microphone_status, # Renamed from SetMicrophoneStatus in GUI.py? Check GUI.py for exact name
        answer_modifier, # Renamed from AnswerModifier? Check GUI.py
        query_modifier, # Renamed from QueryModifier? Check GUI.py
        get_microphone_status, # Renamed from GetMicrophoneStatus? Check GUI.py
        get_assistant_status # Renamed from GetAssistantStatus? Check GUI.py
    )
    # NOTE: I noticed GUI.py uses snake_case (e.g., set_microphone_status) for the helper functions,
    # while main.py was using PascalCase (e.g., SetMicrophoneStatus).
    # I've updated the imports above to use snake_case based on GUI.py.
    # Please double-check the exact function names defined in your final GUI.py if errors persist.

    logging.info("Successfully imported components from Frontend.GUI")
except ImportError as e:
    logging.critical(f"Error importing from Frontend.GUI: {e}", exc_info=True)
    logging.critical(f"Current sys.path: {sys.path}")
    logging.critical("Please ensure GUI.py is in the Frontend directory relative to main.py, PyQt5 is installed, and exported names match.")
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        if QApplication.instance() is None: _app = QApplication(sys.argv) # Dummy app needed if GUI not running
        QMessageBox.critical(None, "Import Error", f"Error importing GUI components: {e}\n\nPlease ensure GUI.py is in the Frontend directory, PyQt5 is installed, and function/variable names match.")
    except ImportError: print("CRITICAL: PyQt5 not found. Cannot display graphical error message.")
    input("Press Enter to exit...")
    sys.exit(1)
except Exception as e:
    logging.critical(f"An unexpected error occurred during GUI import: {e}", exc_info=True)
    input("Press Enter to exit...")
    sys.exit(1)


# --- Attempt to import Backend components ---
try:
    from Backend.Chatbot import ChatBot
    from Backend.Model import FirstLayerDMM
    from Backend.RealtimeSearchEngine import RealtimeSearchEngine
    from Backend.Automation import automate as Automation
    from Backend.SpeechToText import SpeechRecognition
    from Backend.TextToSpeech import text_to_speech as TextToSpeech
    logging.info("Successfully imported components from Backend")
except ImportError as e:
    logging.critical(f"Error importing from Backend: {e}", exc_info=True)
    logging.critical(f"Current sys.path: {sys.path}")
    logging.critical("Please ensure Backend modules are available relative to main.py and dependencies are installed.")
    input("Press Enter to exit...")
    sys.exit(1)
except Exception as e:
    logging.critical(f"An unexpected error occurred during Backend import: {e}", exc_info=True)
    input("Press Enter to exit...")
    sys.exit(1)

# ─── PATH HELPER ──────────────────────────────────────────────────────────────
def resource_path(relative_path):
    """Get absolute path for PyInstaller and dev mode"""
    try:
        base_path = sys._MEIPASS
        logging.info(f"Running in frozen mode (PyInstaller). Base path: {base_path}")
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
        logging.info(f"Running in development mode. Base path: {base_path}")
    return os.path.join(base_path, relative_path)

# ─── CONFIG & LOGGING ─────────────────────────────────────────────────────────
try:
    dotenv_path = resource_path('.env')
    if not os.path.exists(dotenv_path): dotenv_path = resource_path('../.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)
        logging.info(f"Loaded .env file from: {dotenv_path}")
    else:
        logging.warning(f"Warning: .env file not found at {resource_path('.env')} or {resource_path('../.env')}. Using default values or environment variables.")
except Exception as e:
    logging.error(f"Warning: Error loading .env file: {e}. Using default values or environment variables.", exc_info=True)

USERNAME = os.getenv("Username", "User")
ASSISTANT_NAME = os.getenv("Assistantname", "Assistant")
DEFAULT_MESSAGE_USER = f"{USERNAME}: Hello {ASSISTANT_NAME}, How are you?"
DEFAULT_MESSAGE_ASSISTANT = f"{ASSISTANT_NAME}: Welcome {USERNAME}. I am doing well. How may I help you?"

# ─── GLOBAL PATHS & STATE ───────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(resource_path('.'))
logging.info(f"Base directory detected: {BASE_DIR}")
DATA_DIR = os.path.join(BASE_DIR, "Data")
os.makedirs(DATA_DIR, exist_ok=True)
CHATLOG_PATH = os.path.join(DATA_DIR, "ChatLog.json")
logging.info(f"Chatlog path set to: {CHATLOG_PATH}")

# TEMP_DIR_PATH is now imported directly from GUI.py

SUBPROCESS_LIST = []
FUNCTIONS = ["open", "close", "play", "system", "content", "google search", "Youtube"]
EXIT_REQUESTED = False

# ─── INITIALIZATION & CHAT HISTORY HELPERS ─────────────────────────────────────

def ensure_chatlog_exists():
    """Creates an empty chatlog JSON file if it doesn't exist."""
    if not os.path.exists(CHATLOG_PATH):
        logging.info(f"Chatlog file not found at {CHATLOG_PATH}. Creating empty file.")
        try:
            with open(CHATLOG_PATH, "w", encoding="utf-8") as f: json.dump([], f)
        except IOError as e:
            logging.error(f"Failed to create chatlog file at {CHATLOG_PATH}: {e}", exc_info=True)
            raise

def load_and_display_chat_history():
    """Loads chat history from ChatLog.json and displays it on the GUI via show_text_to_screen."""
    ensure_chatlog_exists()
    formatted_messages = []
    try:
        with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
            try:
                messages = json.load(f)
                if not isinstance(messages, list):
                    logging.warning(f"Chatlog file {CHATLOG_PATH} invalid. Resetting.")
                    messages = []
            except json.JSONDecodeError:
                logging.warning(f"Chatlog file {CHATLOG_PATH} corrupted/empty. Resetting.")
                messages = []

        if messages:
            for entry in messages:
                role = entry.get("role")
                text = entry.get("content", "").strip()
                if not text: continue
                prefix = f"{USERNAME}: " if role == "user" else f"{ASSISTANT_NAME}: " if role == "assistant" else ""
                formatted_messages.append(f"{prefix}{text}")
        else:
            logging.info("Chatlog is empty. Displaying default welcome message.")
            formatted_messages.append(DEFAULT_MESSAGE_USER)
            formatted_messages.append(DEFAULT_MESSAGE_ASSISTANT)

        # Use the imported TEMP_DIR_PATH variable
        resp_path = os.path.join(TEMP_DIR_PATH, "Responses.data")
        try:
            with open(resp_path, "w", encoding="utf-8") as f: f.write("") # Clear the file
            logging.info(f"Cleared display file: {resp_path}")
        except IOError as e:
            logging.error(f"Failed to clear display file {resp_path}: {e}", exc_info=True)

        for msg in formatted_messages:
            # Use the imported answer_modifier (assuming it's correct name from GUI.py)
            show_text_to_screen(answer_modifier(msg))
        logging.info(f"Loaded {len(formatted_messages)} messages onto GUI display.")

    except IOError as e:
        logging.error(f"Failed to read chatlog file {CHATLOG_PATH}: {e}", exc_info=True)
        show_text_to_screen(answer_modifier(DEFAULT_MESSAGE_USER))
        show_text_to_screen(answer_modifier(DEFAULT_MESSAGE_ASSISTANT))
    except Exception as e:
        logging.error(f"Error during chat history loading: {e}", exc_info=True)
        show_text_to_screen(f"{ASSISTANT_NAME}: Error loading chat history.")

def save_message_to_chatlog(role: str, text: str):
    """Appends a message to the ChatLog.json file."""
    ensure_chatlog_exists()
    new_message = {"role": role, "content": text.strip()}
    try:
        with open(CHATLOG_PATH, "r+", encoding="utf-8") as f:
            try:
                messages = json.load(f)
                if not isinstance(messages, list): messages = []
            except json.JSONDecodeError: messages = []
            messages.append(new_message)
            f.seek(0); f.truncate()
            json.dump(messages, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Failed to save message to chatlog file {CHATLOG_PATH}: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Error during chatlog saving: {e}", exc_info=True)


def initial_setup():
    """Performs initial setup tasks."""
    logging.info("Performing initial setup...")
    try:
        # Use the imported TEMP_DIR_PATH variable
        os.makedirs(TEMP_DIR_PATH, exist_ok=True)
        logging.info(f"Temporary directory confirmed/created: {TEMP_DIR_PATH}")

        # Use imported set_microphone_status (assuming correct name)
        set_microphone_status(False) # Start with mic off
        set_assistant_status("Initializing...")

        load_and_display_chat_history()

        set_assistant_status("Available...")
        logging.info("Initial setup completed.")
    except Exception as e:
        logging.critical(f"FATAL ERROR during initial setup: {e}", exc_info=True)
        try:
            show_text_to_screen(f"{ASSISTANT_NAME}: CRITICAL ERROR during initialization.")
            set_assistant_status("Error!")
        except Exception as ie: logging.error(f"Could not display initialization error: {ie}")
        raise


# ─── COMMAND HANDLERS ─────────────────────────────────────────────────────────
def handle_general(query: str):
    """Handles general queries using the ChatBot."""
    logging.info(f"Handling general query: {query[:50]}...")
    set_assistant_status("Thinking...")
    # Use imported query_modifier
    modified_query = query_modifier(query)
    try:
        response = ChatBot(modified_query).strip()
        logging.info(f"ChatBot response: {response[:50]}...")
        set_assistant_status("Answering...")
        # Use imported answer_modifier
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {response}"))
        save_message_to_chatlog("assistant", response)
        TextToSpeech(response)
    except Exception as e:
        logging.error(f"Error during ChatBot interaction: {e}", exc_info=True)
        error_message = "Sorry, I encountered an error trying to respond."
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
        save_message_to_chatlog("assistant", error_message)
        TextToSpeech(error_message)
    finally:
        # Use imported get_assistant_status
        if not EXIT_REQUESTED and "Available..." not in get_assistant_status():
             set_assistant_status("Available...")


def handle_realtime(query: str):
    """Handles queries requiring real-time search."""
    logging.info(f"Handling real-time query: {query[:50]}...")
    set_assistant_status("Searching...")
    # Use imported query_modifier
    modified_query = query_modifier(query)
    try:
        response = RealtimeSearchEngine(modified_query).strip()
        logging.info(f"RealtimeSearch response: {response[:50]}...")
        set_assistant_status("Answering...")
        # Use imported answer_modifier
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {response}"))
        save_message_to_chatlog("assistant", response)
        TextToSpeech(response)
    except Exception as e:
        logging.error(f"Error during RealtimeSearchEngine interaction: {e}", exc_info=True)
        error_message = "Sorry, I couldn't complete the search."
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
        save_message_to_chatlog("assistant", error_message)
        TextToSpeech(error_message)
    finally:
        # Use imported get_assistant_status
        if not EXIT_REQUESTED and "Available..." not in get_assistant_status():
             set_assistant_status("Available...")

def handle_image_generation(prompt: str):
    """Handles image generation requests."""
    logging.info(f"Handling image generation request: {prompt[:50]}...")
    set_assistant_status("Generating Image...")
    # Use imported TEMP_DIR_PATH variable
    img_comm_file = os.path.join(TEMP_DIR_PATH, "imageGeneration.data")
    img_result_file = os.path.join(TEMP_DIR_PATH, "GeneratedImage.data")

    try:
        with open(img_comm_file, "w", encoding="utf-8") as f: f.write(f"{prompt},True")
        logging.info(f"Wrote image prompt to trigger file: {img_comm_file}")
        with open(img_result_file, "w", encoding="utf-8") as f: f.write("")
        logging.info(f"Cleared previous image result file: {img_result_file}")

        script_path = resource_path(os.path.join("Backend", "ImageGeneration.py"))
        if not os.path.exists(script_path):
             logging.error(f"Image generation script not found at {script_path}")
             error_message = "Sorry, the image generation module is missing."
             show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
             save_message_to_chatlog("assistant", error_message)
             TextToSpeech(error_message)
             set_assistant_status("Available...")
             with open(img_comm_file, "w", encoding="utf-8") as f: f.write("Error,False")
             return

        logging.info(f"Launching image generation script: {script_path}")
        creationflags = 0
        if platform.system() == "Windows": creationflags = subprocess.CREATE_NO_WINDOW
        proc = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
        SUBPROCESS_LIST.append(proc)

        confirmation_message = f"Okay, I'm starting to generate an image based on: {prompt[:30]}..."
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {confirmation_message}"))
        save_message_to_chatlog("assistant", confirmation_message)
        TextToSpeech(confirmation_message)

    except Exception as e:
        logging.error(f"Error initiating image generation: {e}", exc_info=True)
        error_message = "Sorry, I couldn't start the image generation process."
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
        save_message_to_chatlog("assistant", error_message)
        TextToSpeech(error_message)
        set_assistant_status("Available...")
        try:
            with open(img_comm_file, "w", encoding="utf-8") as f: f.write("Error,False")
        except Exception: pass


def sanitize_automation_cmd(cmd: str) -> tuple[str, str]:
    """Splits command into function and argument, sanitizes argument."""
    parts = cmd.strip().split(None, 1)
    func = parts[0].lower() if parts else ""
    raw_arg = parts[1] if len(parts) > 1 else ""
    sanitized_arg = re.sub(r"[()]", "", raw_arg).strip()
    return func, sanitized_arg

def handle_url_open(arg: str):
    """Opens a URL if valid, otherwise treats as a file/app open command."""
    arg = arg.strip()
    logging.info(f"Attempting to open: {arg}")
    try:
        parsed = urlparse(arg)
        is_url = (parsed.scheme in ("http", "https")) or (not parsed.scheme and parsed.path.lower().startswith("www."))
        if is_url:
            url = arg if parsed.scheme else f"https://{arg}"
            logging.info(f"Identified as URL, opening: {url}")
            webbrowser.open(url)
            set_assistant_status("Opening URL...")
            response_text = f"Opening {arg} in your web browser."
            show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {response_text}"))
            save_message_to_chatlog("assistant", response_text)
            TextToSpeech(f"Opening {arg.split('.')[0]}")
            set_assistant_status("Available...")
        else:
            logging.info(f"Not a standard URL, treating as automation 'open {arg}'")
            execute_automation_command(f"open {arg}")
    except Exception as e:
        logging.error(f"Error handling open command for '{arg}': {e}", exc_info=True)
        error_message = f"Sorry, I couldn't open '{arg}'."
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
        save_message_to_chatlog("assistant", error_message)
        TextToSpeech(error_message)
        set_assistant_status("Available...")


def execute_automation_command(command: str):
    """Executes a command using the Automation module."""
    logging.info(f"Executing automation command: {command}")
    set_assistant_status(f"Executing: {command[:20]}...")
    try:
        asyncio_run(Automation([command]))
        response_text = f"Executed command: {command}."
        logging.info(response_text)
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {response_text}"))
        save_message_to_chatlog("assistant", response_text)
        action_verb = command.split()[0].capitalize()
        TextToSpeech(f"Executed {action_verb}")
    except Exception as e:
        logging.error(f"Error executing automation command '{command}': {e}", exc_info=True)
        error_message = f"Sorry, I failed to execute: {command}."
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
        save_message_to_chatlog("assistant", error_message)
        TextToSpeech("Sorry, I couldn't do that.")
    finally:
        # Use imported get_assistant_status
         if not EXIT_REQUESTED and "Available..." not in get_assistant_status():
             set_assistant_status("Available...")


def handle_dmm_decisions(decisions: list[str], original_query: str):
    """Processes decisions from FirstLayerDMM, routing to appropriate handlers."""
    global EXIT_REQUESTED
    if EXIT_REQUESTED: return

    logging.info(f"DMM Decisions: {decisions}")
    if not decisions:
        logging.warning("FirstLayerDMM returned no decisions. Falling back to general handler.")
        handle_general(original_query)
        return

    exit_cmds = ["exit", "quit", "goodbye", "bye", "shutdown"]
    if any(d.strip().lower() in exit_cmds for d in decisions):
        logging.info("Exit command detected in decisions.")
        set_assistant_status("Shutting down...")
        response_text = f"Goodbye {USERNAME}!"
        show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {response_text}"))
        TextToSpeech(response_text)
        EXIT_REQUESTED = True
        try:
             set_assistant_status("EXIT_REQUESTED") # Signal GUI via status file
             logging.info("Set status to EXIT_REQUESTED for GUI.")
        except Exception as e: logging.error(f"Failed to set EXIT_REQUESTED status: {e}")
        return

    executed_automation = False
    for d in decisions:
        func, arg = sanitize_automation_cmd(d)
        if func in FUNCTIONS:
            logging.info(f"Prioritizing automation command: {d}")
            if func == "open": handle_url_open(arg)
            else: execute_automation_command(d)
            executed_automation = True
            break
    if executed_automation: return

    image_cmds = [d for d in decisions if d.strip().lower().startswith("generate ")]
    if image_cmds:
        prompt = image_cmds[0].strip()[len("generate "):].strip()
        if prompt:
            logging.info(f"Prioritizing image generation with prompt: {prompt[:50]}...")
            handle_image_generation(prompt)
        else:
            logging.warning("Image generation command found, but prompt is empty.")
            handle_general("You asked me to generate an image, but didn't provide a description.")
        return

    realtime_cmds = [d for d in decisions if d.strip().lower().startswith("realtime ")]
    if realtime_cmds:
        combined_query = " and ".join([d.strip()[len("realtime "):].strip() for d in realtime_cmds])
        if not combined_query: combined_query = original_query
        logging.info(f"Handling combined real-time query: {combined_query[:50]}...")
        handle_realtime(combined_query)
        return

    general_cmds = [d for d in decisions if d.strip().lower().startswith("general ")]
    if general_cmds:
        combined_query = " ".join([d.strip()[len("general "):].strip() for d in general_cmds])
        if not combined_query: combined_query = original_query
        logging.info(f"Handling combined general query: {combined_query[:50]}...")
        handle_general(combined_query)
    else:
        logging.info("No specific handler matched DMM decisions. Using original query for general handler.")
        handle_general(original_query)


# ─── CORE EXECUTION FLOW ──────────────────────────────────────────────────────

def microphone_thread_loop():
    """Continuously checks microphone status and triggers main execution if active."""
    global EXIT_REQUESTED
    logging.info("Microphone monitoring thread started.")
    while not EXIT_REQUESTED:
        try:
            # Use imported get_microphone_status (returns bool)
            mic_on = get_microphone_status()
            if mic_on:
                # Use imported get_assistant_status
                current_status = get_assistant_status()
                if "Listening..." not in current_status and "Thinking..." not in current_status \
                   and "Answering..." not in current_status and "Executing..." not in current_status \
                   and "Searching..." not in current_status and "Generating..." not in current_status:
                    main_execution_cycle()
                else: sleep(0.1)
            else:
                # Use imported get_assistant_status
                current_status = get_assistant_status()
                if "Available..." not in current_status and "Error" not in current_status \
                    and "Shutting down..." not in current_status and not EXIT_REQUESTED \
                    and "EXIT_REQUESTED" not in current_status:
                    if "Generating Image..." not in current_status:
                         set_assistant_status("Available...")
                sleep(0.2)
        except Exception as e:
            logging.error(f"Error in microphone_thread_loop: {e}", exc_info=True)
            sleep(5)
    logging.info("Microphone monitoring thread finished.")


def main_execution_cycle():
    """Handles one cycle of listening, processing, and responding."""
    global EXIT_REQUESTED
    if EXIT_REQUESTED: return

    logging.info("--- Start Main Execution Cycle ---")
    query = ""
    try:
        set_assistant_status("Listening...")
        # Use imported get_microphone_status
        if not get_microphone_status():
            logging.warning("main_execution_cycle called but mic status is not True. Aborting cycle.")
            set_assistant_status("Available...")
            return

        query = SpeechRecognition()
        if EXIT_REQUESTED: return

        if not query or query.strip() == "":
            logging.info("Speech Recognition returned no query.")
            set_assistant_status("Available...")
            return

        logging.info(f"User query: '{query}'")
        # Use imported answer_modifier
        show_text_to_screen(answer_modifier(f"{USERNAME}: {query}"))
        save_message_to_chatlog("user", query)
        set_assistant_status("Thinking...")
        decisions = FirstLayerDMM(query)
        handle_dmm_decisions(decisions, query)

    except Exception as e:
        logging.error(f"Error in main_execution_cycle (Query: '{query}'): {e}", exc_info=True)
        error_message = "Sorry, an unexpected error occurred while processing your request."
        try:
            show_text_to_screen(answer_modifier(f"{ASSISTANT_NAME}: {error_message}"))
            save_message_to_chatlog("assistant", error_message)
            TextToSpeech(error_message)
        except Exception as ie: logging.error(f"Failed to report main execution error: {ie}")
        finally:
             if not EXIT_REQUESTED:
                 set_assistant_status("Error!")
                 sleep(2)
                 set_assistant_status("Available...")
    finally:
        # Use imported get_assistant_status
        current_status = get_assistant_status()
        if not EXIT_REQUESTED and "Available..." not in current_status \
           and "Shutting down..." not in current_status \
           and "EXIT_REQUESTED" not in current_status \
           and "Generating Image..." not in current_status:
            set_assistant_status("Available...")
        logging.info("--- End Main Execution Cycle ---")


def run_app():
    """Initializes, starts threads, runs the GUI, and handles cleanup."""
    global EXIT_REQUESTED
    EXIT_REQUESTED = False
    mic_thread = None

    try:
        initial_setup()
        mic_thread = threading.Thread(target=microphone_thread_loop, daemon=True)
        mic_thread.start()
        logging.info("Starting graphical_user_interface()...")
        graphical_user_interface()
        logging.info("graphical_user_interface() has returned. Signaling exit.")
    except Exception as e:
        logging.critical(f"An uncaught exception occurred in run_app: {e}", exc_info=True)
        traceback.print_exc()
    finally:
        logging.info("Initiating shutdown sequence...")
        EXIT_REQUESTED = True
        if mic_thread and mic_thread.is_alive():
            logging.info("Waiting for microphone thread to exit...")
            mic_thread.join(timeout=2)
            if mic_thread.is_alive(): logging.warning("Microphone thread did not exit cleanly.")

        logging.info(f"Terminating {len(SUBPROCESS_LIST)} tracked subprocess(es)...")
        active_subprocesses = [p for p in SUBPROCESS_LIST if p.poll() is None]
        logging.info(f"Found {len(active_subprocesses)} active subprocess(es).")
        for proc in active_subprocesses:
            try:
                logging.info(f"Terminating process {proc.pid}...")
                proc.terminate()
                proc.wait(timeout=0.5)
                if proc.poll() is None:
                    logging.warning(f"Process {proc.pid} did not terminate gracefully. Killing.")
                    proc.kill()
                    proc.wait(timeout=0.5)
            except ProcessLookupError: logging.warning(f"Process {proc.pid} already finished.")
            except Exception as e: logging.error(f"Error terminating subprocess {proc.pid}: {e}", exc_info=True)
        SUBPROCESS_LIST.clear()
        logging.info("Shutdown sequence complete.")

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info(f"Running on Python {sys.version}")
    logging.info(f"Platform: {platform.system()} ({platform.release()})")
    try:
        run_app()
    except SystemExit as e:
         logging.info(f"Application exited with code: {e.code}")
         sys.exit(e.code)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting.")
    except Exception as e:
        logging.critical("An unhandled exception reached the main entry point.", exc_info=True)
        input("A critical error occurred. Press Enter to exit.")
        sys.exit(1)
    finally:
        logging.info("Application has finished.")