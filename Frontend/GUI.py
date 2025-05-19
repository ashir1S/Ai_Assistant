# -*- coding: utf-8 -*-
import sys
import os
import platform
import traceback
import logging
from typing import Optional, Tuple, Union

# --- PyQt5 Imports ---
# Using try-except to handle potential ImportError if PyQt5 is not installed
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QStackedWidget,
                                 QWidget, QLineEdit, QGridLayout, QVBoxLayout, QHBoxLayout,
                                 QPushButton, QLabel, QSizePolicy, QFrame, QDesktopWidget)
    from PyQt5.QtGui import (QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont,
                             QPixmap, QTextBlockFormat, QScreen, QTextCursor)
    from PyQt5.QtCore import (Qt, QSize, QTimer, QEvent, QPoint, QRect, pyqtSignal, QObject) # Added pyqtSignal, QObject
except ImportError:
    print("ERROR: PyQt5 library not found. Please install it using 'pip install PyQt5'")
    sys.exit(1) # Exit if PyQt5 is missing

# --- Other Imports ---
try:
    from dotenv import dotenv_values
except ImportError:
    print("Warning: python-dotenv library not found. .env file will not be loaded. Install using 'pip install python-dotenv'")
    dotenv_values = None # Define a fallback

# --- Logging Setup ---
# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO, # Set default level (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__) # Get a logger instance for this module

# --- Helper Functions ---

def resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = str(sys._MEIPASS)
        log.debug(f"Running bundled (PyInstaller detected _MEIPASS): {base_path}")
    except AttributeError:
        # If not running as a bundled app, use the script's directory
        base_path = os.path.abspath(".")
        log.debug(f"Running from script, base path: {base_path}")

    full_path = os.path.join(base_path, relative_path)
    # log.debug(f"Resolved resource path for '{relative_path}' to '{full_path}'") # Can be noisy
    return full_path

def get_script_directory() -> str:
    """Determines the script's directory reliably."""
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable (e.g., PyInstaller)
        script_dir = os.path.dirname(sys.executable)
        log.info(f"Running as bundled executable. Script dir: {script_dir}")
    else:
        # If running as a standard Python script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log.info(f"Running as standard script. Script dir: {script_dir}")
    return script_dir

# --- Configuration and Constants ---
SCRIPT_DIR = get_script_directory()
# Assume .env is in the same directory as the script/executable
ENV_PATH = os.path.join(SCRIPT_DIR, '.env')
# Persistent data directory (e.g., for status files) relative to script/exe
TEMP_DIR_PATH = os.path.join(SCRIPT_DIR, "Files")
# Graphics directory relative to script/exe (ensure it's included by PyInstaller)
GRAPHICS_DIR = os.path.join("Graphics") # Relative path for resource_path

# --- Load Environment Variables ---
ASSISTANT_NAME = "Assistant" # Default value
if dotenv_values:
    try:
        if os.path.exists(ENV_PATH):
            env_vars = dotenv_values(ENV_PATH)
            ASSISTANT_NAME = env_vars.get("Assistantname", ASSISTANT_NAME)
            log.info(f"Loaded Assistantname '{ASSISTANT_NAME}' from {ENV_PATH}")
        else:
            log.warning(f".env file not found at '{ENV_PATH}'. Using default values.")
    except Exception as e:
        log.error(f"Could not load .env file. Using default values. Error: {e}", exc_info=True)
else:
    log.warning("python-dotenv not installed, cannot load .env file.")

# --- Ensure Persistent Data Directory Exists ---
try:
    os.makedirs(TEMP_DIR_PATH, exist_ok=True)
    log.info(f"Ensured persistent data directory exists: {TEMP_DIR_PATH}")
except OSError as e:
    log.critical(f"Failed to create persistent data directory '{TEMP_DIR_PATH}': {e}", exc_info=True)
    # Depending on severity, you might want to exit here
    # sys.exit(1)

# --- Constants for Data Files ---
MIC_DATA_FILE = os.path.join(TEMP_DIR_PATH, "Mic.data")
STATUS_DATA_FILE = os.path.join(TEMP_DIR_PATH, "Status.data")
RESPONSES_DATA_FILE = os.path.join(TEMP_DIR_PATH, "Responses.data")
GENERATED_IMAGE_DATA_FILE = os.path.join(TEMP_DIR_PATH, "GeneratedImage.data")

# --- Global State (Minimize usage - consider passing state or using signals) ---
# This is kept for now to match the original structure, but ideally ChatSection manages its own state
old_chat_message = ""

# --- File I/O Helper Functions ---

def _safe_file_write(filepath: str, content: str):
    """Safely writes content to a file."""
    try:
        # Ensure directory exists before writing (redundant if TEMP_DIR_PATH check passed, but safe)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding='utf-8') as file:
            file.write(content)
        # log.debug(f"Successfully wrote to {filepath}") # Optional: uncomment for verbose logging
    except IOError as e:
        log.error(f"Error writing to file {filepath}: {e}", exc_info=True)
    except Exception as e:
        log.error(f"Unexpected error writing to file {filepath}: {e}", exc_info=True)

def _safe_file_read(filepath: str) -> Optional[str]:
    """Safely reads content from a file, creating it with defaults if missing."""
    try:
        filename = os.path.basename(filepath)
        # Ensure directory exists before reading/writing
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        if not os.path.exists(filepath):
            default_content = ""
            if filename == os.path.basename(MIC_DATA_FILE):
                default_content = "False"
            elif filename == os.path.basename(STATUS_DATA_FILE):
                default_content = "Initializing..."
            elif filename == os.path.basename(RESPONSES_DATA_FILE):
                default_content = "" # Default responses is empty
            elif filename == os.path.basename(GENERATED_IMAGE_DATA_FILE):
                 default_content = "" # Default is empty path

            log.warning(f"File '{filepath}' not found. Creating with default content: '{default_content}'")
            _safe_file_write(filepath, default_content)
            return default_content # Return the default immediately

        # If file exists, read it
        with open(filepath, "r", encoding='utf-8') as file:
            content = file.read()
            # log.debug(f"Successfully read from {filepath}") # Optional: uncomment for verbose logging
            return content
    except IOError as e:
        log.error(f"IOError reading from file {filepath}: {e}", exc_info=True)
    except Exception as e:
        log.error(f"Unexpected error reading file {filepath}: {e}", exc_info=True)

    # Fallback return if reading failed after file existence check
    log.warning(f"Failed to read existing file {filepath}. Returning default based on filename.")
    filename = os.path.basename(filepath)
    if filename == os.path.basename(MIC_DATA_FILE): return "False"
    if filename == os.path.basename(STATUS_DATA_FILE): return "Initializing..."
    if filename == os.path.basename(GENERATED_IMAGE_DATA_FILE): return ""
    return "" # Default fallback

# --- Status/Data Management Functions (Using Files - Replace with Signals/IPC if possible) ---

def set_microphone_status(command: bool):
    """Sets the microphone status ('True' or 'False') in Mic.data."""
    _safe_file_write(MIC_DATA_FILE, str(command))
    log.info(f"Microphone status set to: {command}")

def get_microphone_status() -> bool:
    """Gets the microphone status from Mic.data."""
    status_str = _safe_file_read(MIC_DATA_FILE)
    return str(status_str).strip().lower() == "true"

def set_assistant_status(status: str):
    """Sets the assistant's current status text in Status.data."""
    _safe_file_write(STATUS_DATA_FILE, status)
    # log.debug(f"Assistant status set to: {status}") # Can be noisy

def get_assistant_status() -> str:
    """Gets the assistant's current status text from Status.data."""
    return _safe_file_read(STATUS_DATA_FILE) or "Unknown" # Ensure it returns a string

def show_text_to_screen(text: str):
    """Writes text to the Responses.data file for display."""
    _safe_file_write(RESPONSES_DATA_FILE, text)
    # log.debug(f"Wrote to Responses.data: '{text[:50]}...'") # Log snippet

# --- Text Processing Helpers ---

def answer_modifier(answer: Optional[str]) -> str:
    """Removes empty lines from the answer string."""
    if not answer:
        return ""
    lines = answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def query_modifier(query: Optional[str]) -> str:
    """Formats the query: lowercase, strip, capitalize, add period if question."""
    if not query:
        return ""
    new_query = query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's"]

    is_question = any(new_query.startswith(word + " ") for word in question_words)

    if is_question:
        if query_words and query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        elif not new_query.endswith('.'):
            new_query += "."

    # Capitalize the first letter
    if new_query:
        new_query = new_query[0].upper() + new_query[1:]
    return new_query

# --- Path Helpers ---

def graphics_directory_path(filename: str) -> str:
    """Returns the correct path for a graphics file using resource_path."""
    return resource_path(os.path.join(GRAPHICS_DIR, filename))

# TempDirectoryPath is now the global TEMP_DIR_PATH

# --- Mic Button Actions ---

def mic_button_initialed():
    """Action when mic button is toggled OFF (set to False)."""
    set_microphone_status(False)

def mic_button_closed():
    """Action when mic button is toggled ON (set to True)."""
    set_microphone_status(True)

# --- GUI Classes ---

class ChatSection(QWidget):
    """Widget displaying the chat messages and assistant status/animation."""
    # Define signals for potential future use (if backend runs in a thread)
    # status_updated = pyqtSignal(str)
    # message_received = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        log.info("Initializing ChatSection...")
        self._last_displayed_message = "" # Internal state for comparison
        self._last_status = "" # Internal state for status comparison
        self._setup_ui()
        self._setup_timer()
        log.info("ChatSection initialization complete.")

    def _setup_ui(self):
        """Creates the UI elements for the chat section."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.chat_text_edit = QTextEdit()
        self.chat_text_edit.setReadOnly(True)
        self.chat_text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.chat_text_edit.setFrameStyle(QFrame.NoFrame)
        font = QFont("Segoe UI", 14) # Adjusted font size slightly intial 11
        self.chat_text_edit.setFont(font)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        bottom_layout.setSpacing(15)

        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setStyleSheet("color: #aaaaaa; font-size: 10pt; border: none; background-color: transparent;")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none; background-color: transparent;")
        self.movie = None
        self._load_gif()

        self.gif_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bottom_layout.addWidget(self.status_label)
        # bottom_layout.addWidget(self.gif_label)

        layout.addWidget(self.chat_text_edit, 1) # Chat text takes expanding space
        layout.addLayout(bottom_layout)

        self.setStyleSheet("background-color: #121212;")
        self.chat_text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; color: #f0f0f0; border: none; padding: 10px;
                font-family: "Segoe UI", sans-serif;
            }
            QScrollBar:vertical {
                border: none; background: #1e1e1e; width: 10px; margin: 0px; border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555; min-height: 30px; border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover { background: #666666; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

    def _load_gif(self):
        """Loads and configures the status GIF."""
        try:
            gif_path = graphics_directory_path('Jarvis.gif')
            log.info(f"ChatSection: Attempting to load GIF from: {gif_path}")
            if not os.path.exists(gif_path):
                log.error(f"ChatSection: GIF file not found at path: {gif_path}")
                self.gif_label.setText("(GIF Missing)")
                return

            self.movie = QMovie(gif_path)
            if self.movie.isValid():
                max_gif_size_W = 120 # Slightly smaller
                max_gif_size_H = 67
                target_size = QSize(max_gif_size_W, max_gif_size_H)
                # Use KeepAspectRatioByExpanding for potentially better filling if needed
                scaled_target_size = target_size.scaled(max_gif_size_W, max_gif_size_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.movie.setScaledSize(scaled_target_size)
                self.gif_label.setMovie(self.movie)
                self.gif_label.setFixedSize(scaled_target_size) # Use fixed size for layout stability
                self.movie.start()
                if self.movie.state() != QMovie.Running:
                     log.warning(f"ChatSection: Movie did not start correctly! Path: {gif_path}, Error: {self.movie.lastErrorString()}")
            else:
                self.gif_label.setText("(GIF Error)")
                log.error(f"ChatSection: QMovie is invalid after creation. Path: {gif_path}, Error: {self.movie.lastErrorString()}")

        except Exception as e:
            self.gif_label.setText("(GIF Load Fail)")
            log.error(f"ChatSection: EXCEPTION during GIF loading: {e}", exc_info=True)

    def _setup_timer(self):
        """Sets up the QTimer for polling updates."""
        self.timer = QTimer(self)
        # Connect timer to polling methods
        self.timer.timeout.connect(self._check_for_updates)
        self.timer.start(300) # Check slightly less frequently (adjust as needed)
        log.info("ChatSection timer started.")

    def _check_for_updates(self):
        """Called by the timer to poll for messages and status."""
        self._poll_messages()
        self._poll_status()

    def _poll_messages(self):
        """Loads messages from Responses.data and updates the chat display if changed."""
        # global old_chat_message # Access global (consider removing global later)
        try:
            messages = _safe_file_read(RESPONSES_DATA_FILE)

            # Check if content exists and is different from the last displayed one
            if messages is not None and messages != self._last_displayed_message:
                log.debug("ChatSection: Detected change in Responses.data")
                cleaned_message = answer_modifier(messages)
                if cleaned_message:
                    self.add_message(message=cleaned_message, color='#f0f0f0')
                # Update internal state regardless of whether cleaned message is empty
                self._last_displayed_message = messages
            elif messages == "" and self._last_displayed_message != "":
                # Handle external clearing of the file
                log.info("ChatSection: Responses.data appears cleared externally.")
                self._last_displayed_message = messages # Update internal state

        except Exception as e:
            log.error(f"Error in ChatSection _poll_messages: {e}", exc_info=True)

    def _poll_status(self):
        """Updates the status label AND checks for exit signal."""
        try:
            status_text = get_assistant_status()

            # *** CHECK FOR EXIT SIGNAL ***
            if status_text == "EXIT_REQUESTED":
                log.info("ChatSection: EXIT_REQUESTED status detected, quitting application.")
                QApplication.instance().quit() # Gracefully quit the application
                return # Stop further processing here

            # Update label only if status changed
            if status_text != self._last_status:
                display_text = f"Status: {status_text or 'Idle'}"
                self.status_label.setText(display_text)
                self._last_status = status_text # Update internal state
                # log.debug(f"ChatSection: Status updated to: {status_text}") # Can be noisy

        except Exception as e:
            log.error(f"Error in ChatSection _poll_status: {e}", exc_info=True)

    # --- Public Methods / Slots (for future signal connection) ---
    # @pyqtSlot(str)
    def update_status_display(self, status: str):
         """Updates the status label directly (intended for signal connection)."""
         display_text = f"Status: {status or 'Idle'}"
         self.status_label.setText(display_text)
         self._last_status = status # Keep internal state consistent

    # @pyqtSlot(str)
    def add_message(self, message: str, color: str = '#f0f0f0'):
        """Adds a formatted message to the chat display."""
        try:
            cursor = self.chat_text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)

            is_empty_doc = self.chat_text_edit.document().isEmpty()
            if not is_empty_doc:
                 # Insert a new block (paragraph) for separation only if not the first message
                 cursor.insertBlock()

            char_format = QTextCharFormat()
            char_format.setForeground(QColor(color))
            # Use the font already set on the QTextEdit
            # font = QFont(); font.setPointSize(11); char_format.setFont(font)
            char_format.setFont(self.chat_text_edit.font())

            block_format = QTextBlockFormat()
            block_format.setTopMargin(5)    # Spacing above the block
            block_format.setBottomMargin(5) # Spacing below the block
            block_format.setLeftMargin(10)  # Indentation/Padding
            block_format.setRightMargin(10) # Padding

            cursor.setBlockFormat(block_format) # Apply block formatting first
            cursor.setCharFormat(char_format)   # Then apply character formatting
            cursor.insertText(message)          # Insert the text

            # Ensure the new message is visible
            self.chat_text_edit.ensureCursorVisible()
            log.debug(f"ChatSection: Added message: '{message[:50]}...'")
        except Exception as e:
            log.error(f"Error in ChatSection add_message: {e}", exc_info=True)

    def stop_timer(self):
        """Stops the internal timer."""
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            log.info("ChatSection timer stopped.")


class InitialScreen(QWidget):
    """The initial screen with a large GIF and microphone toggle."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        log.info("Initializing InitialScreen...")
        self._last_status = "" # Internal state for status comparison
        self._setup_ui()
        self._load_mic_icons()
        self._update_mic_icon_visual() # Set initial icon state
        self._setup_timer()
        log.info("InitialScreen initialization complete.")

    def _get_screen_geometry(self) -> QRect:
        """Safely gets the primary screen's available geometry."""
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                screens = QApplication.screens()
                if screens:
                    screen = screens[0]
                    log.warning("Primary screen not found, using first available screen.")
                else:
                    log.error("No screens detected by QApplication.")
                    return QRect(0, 0, 1024, 768) # Fallback default
            geometry = screen.availableGeometry() # Use availableGeometry to avoid docks/taskbars
            log.info(f"Detected available screen geometry: {geometry.width()}x{geometry.height()}")
            return geometry
        except Exception as e:
             log.error(f"Could not get screen geometry: {e}. Using defaults.", exc_info=True)
             return QRect(0, 0, 1024, 768) # Fallback default

    def _setup_ui(self):
        """Creates the UI elements for the initial screen."""
        screen_geometry = self._get_screen_geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # --- GIF Display ---
        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none; background-color: transparent;")
        self.initial_movie = None
        self._load_initial_gif(screen_width, screen_height)
        self.gif_label.setAlignment(Qt.AlignCenter)
        self.gif_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gif_label.setMinimumSize(230, 142) # Minimum size based on aspect ratio 16:9 200 112

        # --- Status Label ---
        self.status_label = QLabel("Status: Initializing...")
        self.status_label.setStyleSheet("color: #cccccc; font-size: 11pt; border: none; background-color: transparent; qproperty-alignment: 'AlignCenter';")

        # --- Mic Icon ---
        self.mic_icon_label = QLabel()
        self.mic_icon_label.setFixedSize(70, 70) # Slightly smaller fixed size for icon container
        self.mic_icon_label.setAlignment(Qt.AlignCenter)
        self.mic_icon_label.setStyleSheet("border: none; background-color: transparent;")
        self.mic_icon_label.setCursor(Qt.PointingHandCursor)
        self.mic_icon_label.mousePressEvent = self._toggle_mic_icon # Connect click event

        # --- Layout Assembly ---
        content_layout.addStretch(1) # Pushes content down
        content_layout.addWidget(self.gif_label) # GIF takes expanding space
        content_layout.addWidget(self.status_label) # Status label below GIF
        content_layout.addWidget(self.mic_icon_label, alignment=Qt.AlignCenter) # Mic icon centered
        content_layout.addStretch(1) # Pushes content up from bottom

        self.setStyleSheet("background-color: #121212;")

    def _load_initial_gif(self, screen_width: int, screen_height: int):
        """Loads and scales the main GIF for the initial screen."""
        try:
            gif_path = graphics_directory_path('Jarvis.gif')
            log.info(f"InitialScreen: Attempting to load GIF from: {gif_path}")
            if not os.path.exists(gif_path):
                log.error(f"InitialScreen: GIF file not found at path: {gif_path}")
                self.gif_label.setText("(GIF Missing)")
                return

            self.initial_movie = QMovie(gif_path)
            if self.initial_movie.isValid():
                # Calculate dynamic size based on screen, with limits
                gif_aspect_ratio = 16 / 9
                max_gif_width = min(screen_width * 0.6, 800) # Limit width
                max_gif_height = min(screen_height * 0.4, 450) # Limit height

                scaled_width = int(max_gif_width)
                scaled_height = int(max_gif_width / gif_aspect_ratio)

                # Adjust if height constraint is hit first
                if scaled_height > max_gif_height:
                    scaled_height = int(max_gif_height)
                    scaled_width = int(max_gif_height * gif_aspect_ratio)

                scaled_size = QSize(scaled_width, scaled_height)
                log.debug(f"InitialScreen: Scaling GIF to {scaled_width}x{scaled_height}")
                self.initial_movie.setScaledSize(scaled_size)
                self.gif_label.setMovie(self.initial_movie)
                self.initial_movie.start()
                if self.initial_movie.state() != QMovie.Running:
                     log.warning(f"InitialScreen: Movie did not start correctly! Path: {gif_path}, Error: {self.initial_movie.lastErrorString()}")
            else:
                self.gif_label.setText("(GIF Error)")
                log.error(f"InitialScreen: QMovie is invalid. Path: {gif_path}, Error: {self.initial_movie.lastErrorString()}")

        except Exception as e:
            self.gif_label.setText("(GIF Load Fail)")
            log.error(f"InitialScreen: EXCEPTION during GIF loading: {e}", exc_info=True)

    def _load_mic_icons(self):
        """Loads and scales the microphone icons."""
        self.mic_on_pixmap: Optional[QPixmap] = None
        self.mic_off_pixmap: Optional[QPixmap] = None
        icon_display_size = 55 # Size to display the icon within the label

        try:
            mic_on_path = graphics_directory_path('Mic_on.png')
            mic_off_path = graphics_directory_path('Mic_off.png')
            log.info(f"InitialScreen: Loading mic icons from: {mic_on_path}, {mic_off_path}")

            temp_mic_on = QPixmap(mic_on_path)
            temp_mic_off = QPixmap(mic_off_path)

            load_success = True
            if temp_mic_on.isNull():
                log.error(f"InitialScreen: Failed to load Mic_on.png from {mic_on_path}")
                load_success = False
            if temp_mic_off.isNull():
                log.error(f"InitialScreen: Failed to load Mic_off.png from {mic_off_path}")
                load_success = False

            if load_success:
                 self.mic_on_pixmap = temp_mic_on.scaled(icon_display_size, icon_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 self.mic_off_pixmap = temp_mic_off.scaled(icon_display_size, icon_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                 log.info("Mic icons loaded and scaled successfully.")
            else:
                 raise ValueError("One or both mic icons failed to load properly.")

        except Exception as e:
            log.error(f"ERROR loading or scaling mic icons: {e}", exc_info=True)
            # Fallback: Create colored squares if icons fail
            fallback_size = icon_display_size
            self.mic_on_pixmap = QPixmap(fallback_size, fallback_size)
            self.mic_on_pixmap.fill(QColor("#4CAF50")) # Greenish
            self.mic_off_pixmap = QPixmap(fallback_size, fallback_size)
            self.mic_off_pixmap.fill(QColor("#F44336")) # Reddish
            log.warning("Using fallback colored squares for mic icons.")

    def _setup_timer(self):
        """Sets up the QTimer for polling status updates."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._poll_status) # Connect timer
        self.timer.start(300) # Check status periodically
        log.info("InitialScreen timer started.")

    def _poll_status(self):
        """Updates the status label AND checks for exit signal."""
        try:
            status_text = get_assistant_status()
            if status_text == "EXIT_REQUESTED":
                log.info("InitialScreen: EXIT_REQUESTED status detected, quitting application.")
                QApplication.instance().quit()
                return

            # Update label only if status changed
            if status_text != self._last_status:
                display_text = f"Status: {status_text or 'Idle'}"
                self.status_label.setText(display_text)
                self._last_status = status_text # Update internal state
                # log.debug(f"InitialScreen: Status updated to: {status_text}") # Can be noisy

        except Exception as e:
            log.error(f"Error in InitialScreen _poll_status: {e}", exc_info=True)

    def _update_mic_icon_visual(self):
        """Updates the mic icon label based on the current status from the file."""
        is_mic_on = get_microphone_status()
        if is_mic_on:
            pixmap = self.mic_on_pixmap
            tooltip = "Microphone is ON (Click to turn OFF)"
            fallback_text = "MIC ON"
        else:
            pixmap = self.mic_off_pixmap
            tooltip = "Microphone is OFF (Click to turn ON)"
            fallback_text = "MIC OFF"

        if pixmap and not pixmap.isNull():
            self.mic_icon_label.setPixmap(pixmap)
        else:
            self.mic_icon_label.setText(fallback_text) # Fallback if pixmap loading failed
            log.warning("Mic pixmap invalid or missing, using fallback text.")

        self.mic_icon_label.setToolTip(tooltip)

    def _toggle_mic_icon(self, event: QEvent):
        """Handles clicks on the mic icon label."""
        if event.button() == Qt.LeftButton:
            current_state = get_microphone_status()
            new_state = not current_state
            log.info(f"Mic icon clicked. Current state: {current_state}, New state: {new_state}")
            # Call the appropriate action function to update the data file
            action = mic_button_closed if new_state else mic_button_initialed
            action()
            # Update the visual display immediately
            self._update_mic_icon_visual()
            event.accept()
        else:
            event.ignore()

    def stop_timer(self):
        """Stops the internal timer."""
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()
            log.info("InitialScreen timer stopped.")


class MessageScreen(QWidget):
    """Screen dedicated to showing the ChatSection and the generated image with a close button."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        log.info("Initializing MessageScreen...")
        self._last_checked_image_path = None # Track the last processed image path
        self._setup_ui()
        self._setup_timer()
        log.info("MessageScreen initialization complete.")

    def _setup_ui(self):
        """Creates the UI elements for the message screen."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) # Slightly reduced margins
        layout.setSpacing(10)

        # --- Chat Section ---
        self.chat_section = ChatSection(self)
        layout.addWidget(self.chat_section, 1) # Chat section takes most vertical space

        # --- Image Display Area with Close Button ---
        self.image_container = QFrame(self)
        self.image_container.setObjectName("ImageContainerFrame")
        # Style the container - subtle background and border
        self.image_container.setStyleSheet("""
            #ImageContainerFrame {
                background-color: #1A1A1A; /* Slightly different background */
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)
        image_container_layout = QVBoxLayout(self.image_container)
        image_container_layout.setContentsMargins(5, 5, 5, 5) # Inner padding
        image_container_layout.setSpacing(5)

        # --- Top Bar for Close Button ---
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.addStretch(1) # Push button to the right

        self.image_close_button = QPushButton()
        try:
            close_icon_path = graphics_directory_path('Close.png')
            close_icon = QIcon(close_icon_path)
            if not close_icon.isNull():
                self.image_close_button.setIcon(close_icon)
                self.image_close_button.setIconSize(QSize(16, 16)) # Smaller icon
            else:
                log.warning(f"Failed to load Close.png for image close button, using text 'X'. Path: {close_icon_path}")
                self.image_close_button.setText("X") # Fallback text
                self.image_close_button.setFont(QFont("Arial", 10, QFont.Bold))
        except Exception as e:
             log.error(f"Error loading close icon for image: {e}", exc_info=True)
             self.image_close_button.setText("X") # Fallback text

        # Style the close button: small, flat, red hover
        self.image_close_button.setFixedSize(24, 24)
        self.image_close_button.setCursor(Qt.PointingHandCursor)
        self.image_close_button.setToolTip("Close Image")
        self.image_close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #AAAAAA; /* Default color for 'X' text */
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E81123; /* Red hover */
                color: white; /* White 'X' on hover */
            }
            QPushButton:pressed {
                background-color: #F1707A; /* Lighter red pressed */
            }
        """)
        self.image_close_button.clicked.connect(self._hide_image_container) # Connect click
        top_bar_layout.addWidget(self.image_close_button)
        image_container_layout.addLayout(top_bar_layout) # Add button bar to container

        # --- Image Label ---
        self.image_display_label = QLabel()
        self.image_display_label.setAlignment(Qt.AlignCenter)
        # Let the container manage size, but set a reasonable minimum height for the label
        self.image_display_label.setMinimumHeight(150)
        # Allow label to expand horizontally and vertically within its container
        self.image_display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_display_label.setStyleSheet("border: none; background-color: transparent; color: #888888;")
        self.image_display_label.setText("Generated image will appear here") # Placeholder
        image_container_layout.addWidget(self.image_display_label, 1) # Image label takes remaining space

        self.image_container.setVisible(False)  # Hide the whole container by default
        # Add container to main layout, no stretch factor (takes needed height up to constraints)
        layout.addWidget(self.image_container, 0)

        # --- Screen Background ---
        self.setStyleSheet("background-color: #121212;") # Background for the screen itself

    def _setup_timer(self):
        """Sets up the QTimer to check for new images."""
        self.image_check_timer = QTimer(self)
        self.image_check_timer.timeout.connect(self._check_for_generated_image)
        self.image_check_timer.start(1000)  # Check every 1 second
        log.info("MessageScreen image check timer started.")

    def _check_for_generated_image(self):
        """Checks GeneratedImage.data for a new image path and displays it."""
        try:
            # Read the image path from the status file
            image_path = _safe_file_read(GENERATED_IMAGE_DATA_FILE)

            # --- Conditions to Skip Processing ---
            # 1. Path is empty or None
            if not image_path:
                # If the container is visible and the file is now empty, hide it
                if self.image_container.isVisible():
                     log.info("Image data file is empty, hiding image container.")
                     self._hide_image_container()
                self._last_checked_image_path = None # Reset last path
                return
            # 2. Path is the same as the last one we processed (or tried to process)
            if image_path == self._last_checked_image_path:
                return # Avoid reprocessing the same path

            # --- Process New Path ---
            log.info(f"Detected new image path in data file: '{image_path}'")
            self._last_checked_image_path = image_path # Store the path we are now processing

            # 3. Check if the image file itself exists
            if not os.path.exists(image_path):
                 log.warning(f"Image path found ('{image_path}'), but file does not exist at that location.")
                 # Optionally clear the data file if path is invalid? Or let the backend handle it.
                 # _safe_file_write(GENERATED_IMAGE_DATA_FILE, "") # Clear if invalid
                 self.image_display_label.setText("Image file not found")
                 self.image_container.setVisible(True) # Show container with error
                 return # Stop processing this path

            # --- Load and Display the Image ---
            log.info(f"Loading image from path: {image_path}")
            pixmap = QPixmap(image_path)

            if not pixmap.isNull():
                log.info("Pixmap loaded successfully.")
                # Scale the pixmap to fit the container width, respecting aspect ratio
                # Use the image_display_label's current width as a guide, but provide a fallback
                container_width = self.image_display_label.width()
                if container_width <= 10: container_width = 600 # Use a sensible default if layout hasn't updated yet
                # Scale to width, height will adjust automatically with KeepAspectRatio
                scaled_pixmap = pixmap.scaledToWidth(container_width, Qt.SmoothTransformation)

                self.image_display_label.setPixmap(scaled_pixmap)
                self.image_container.setVisible(True) # Make the container visible
                # Adjust container height dynamically if needed (optional)
                # self.image_container.setFixedHeight(scaled_pixmap.height() + 40) # + padding/button space
                log.info(f"Image displayed. Original: {pixmap.width()}x{pixmap.height()}, Scaled width: {scaled_pixmap.width()}")

                # Clear the status file ONLY AFTER successfully loading and displaying?
                # Or maybe the backend should clear it after writing?
                # For now, let's assume the backend manages clearing it or overwriting it.
                # If you want the GUI to clear it:
                # _safe_file_write(GENERATED_IMAGE_DATA_FILE, "")
                # log.info(f"Cleared image data file: {GENERATED_IMAGE_DATA_FILE}")

            else:
                # Pixmap is null - the file might not be a valid image format
                log.error(f"Failed to load QPixmap from path: {image_path}. Is it a valid image file?")
                self.image_display_label.setText("Error loading image") # Show error in label
                self.image_container.setVisible(True) # Show container with error
                # Optionally clear the data file even on load error
                # _safe_file_write(GENERATED_IMAGE_DATA_FILE, "")

        except IOError as e:
             log.error(f"IOError accessing generated image data file: {e}", exc_info=True)
        except Exception as e:
            log.error(f"Unexpected error loading/displaying generated image: {e}", exc_info=True)
            # Optionally show an error message in the display
            # self.image_display_label.setText("Error processing image")
            # self.image_container.setVisible(True)

    def _hide_image_container(self):
        """Hides the image container and clears the pixmap."""
        if self.image_container.isVisible():
            self.image_container.setVisible(False)
            self.image_display_label.clear() # Clear the pixmap
            self.image_display_label.setText("Generated image will appear here") # Reset placeholder
            log.info("Image container hidden by user.")
            # Do NOT clear the GeneratedImage.data file here,
            # as the image might still be valid if the user wants to see it again later
            # (unless the backend generates a new one).
            # Also, don't reset _last_checked_image_path here.

    def stop_timers(self):
        """Stops timers in this screen and its children."""
        if hasattr(self, 'image_check_timer') and self.image_check_timer.isActive():
            self.image_check_timer.stop()
            log.info("MessageScreen image check timer stopped.")
        if hasattr(self, 'chat_section'):
            self.chat_section.stop_timer() # Delegate stopping chat timer


class CustomTopBar(QWidget):
    """Custom top bar with title, navigation, and window controls."""
    def __init__(self, parent_window: QMainWindow, stacked_widget: QStackedWidget):
        super().__init__(parent_window)
        log.info("Initializing CustomTopBar...")
        self.parent_window = parent_window
        self.stacked_widget = stacked_widget
        self.offset: Optional[QPoint] = None # For window dragging
        self._setup_ui()
        # Update maximize icon state after UI is built and window is shown
        QTimer.singleShot(100, self._update_maximize_button_icon) # Short delay
        log.info("CustomTopBar initialization complete.")

    def _setup_ui(self):
        """Creates the UI elements for the top bar."""
        self.setFixedHeight(50) # Fixed height for the top bar
        self.setStyleSheet("""
            QWidget { background-color: #252525; border-bottom: 1px solid #383838; }
        """) # Slightly lighter background
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0) # Left, Top, Right, Bottom margins
        layout.setSpacing(10)

        # --- Title ---
        ASSISTANT_NAME = "NOVA" # Placeholder for the assistant name
        title_label = QLabel(f" {ASSISTANT_NAME.capitalize()}")
        title_label.setStyleSheet("""
            QLabel {
                color: #66bbff; /* Lighter blue */
                font-size: 14pt; /* Use points for font size */
                font-weight: bold;
                padding-left: 5px;
                background-color: transparent;
                border: none;
            }
        """)

        # --- Navigation Buttons ---
        nav_button_style = """
            QPushButton {
                background-color: transparent;
                color: #e0e0e0; /* Lighter text */
                border: none;
                padding: 5px 10px; /* Adjust padding */
                border-radius: 5px;
                font-size: 10pt;
                min-height: 32px; /* Adjust height */
                text-align: left;
            }
            QPushButton:hover { background-color: #3a3a3a; }
            QPushButton:pressed { background-color: #484848; }
            QPushButton:focus { outline: none; }
        """
        nav_icon_size = QSize(22, 22) # Slightly smaller icons

        home_button = self._create_nav_button(" Home", "Home.png", 0, nav_icon_size, nav_button_style)
        message_button = self._create_nav_button(" Chat", "Chats.png", 1, nav_icon_size, nav_button_style)

        # --- Window Control Buttons ---
        control_button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                border-radius: 5px;
                min-width: 38px; max-width: 38px; /* Slightly wider */
                min-height: 32px; max-height: 32px; /* Match nav buttons */
            }
            QPushButton:hover { background-color: #444444; }
            QPushButton:pressed { background-color: #555555; }
            QPushButton:focus { outline: none; }
        """
        control_icon_size = QSize(18, 18) # Smaller control icons

        minimize_button = self._create_control_button('Minimize2.png', self._minimize_window, "Minimize", control_icon_size, control_button_style)
        self.maximize_button = self._create_control_button(None, self._toggle_maximize_window, "Maximize", control_icon_size, control_button_style) # Icon set later
        close_button = self._create_control_button('Close.png', self._close_window, "Close", control_icon_size, control_button_style)
        # Special hover/pressed style for close button
        close_button.setStyleSheet(control_button_style +
            " QPushButton:hover { background-color: #E81123; }"
            " QPushButton:pressed { background-color: #F1707A; }")

        # Load maximize/restore icons separately
        self._load_maximize_restore_icons()
        self._update_maximize_button_icon() # Set initial icon

        # --- Layout Assembly ---
        layout.addWidget(title_label)
        layout.addStretch(1) # Spacer
        layout.addWidget(home_button)
        layout.addWidget(message_button)
        layout.addSpacing(20) # Space before controls
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)

    def _create_nav_button(self, text: str, icon_filename: str, index: int, icon_size: QSize, style: str) -> QPushButton:
        """Helper to create navigation buttons."""
        button = QPushButton(text)
        try:
            icon_path = graphics_directory_path(icon_filename)
            icon = QIcon(icon_path)
            if icon.isNull():
                log.warning(f"Failed to load navigation icon: {icon_filename}. Path: {icon_path}")
            else:
                button.setIcon(icon)
        except Exception as e:
            log.error(f"Error loading navigation icon '{icon_filename}': {e}", exc_info=True)

        button.setIconSize(icon_size)
        button.setStyleSheet(style)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(index))
        return button

    def _create_control_button(self, icon_filename: Optional[str], slot, tooltip: str, icon_size: QSize, style: str) -> QPushButton:
        """Helper to create window control buttons."""
        button = QPushButton()
        if icon_filename:
            try:
                icon_path = graphics_directory_path(icon_filename)
                icon = QIcon(icon_path)
                if icon.isNull():
                    log.warning(f"Failed to load control icon: {icon_filename}. Path: {icon_path}")
                    button.setText(tooltip[0]) # Fallback: First letter
                else:
                    button.setIcon(icon)
            except Exception as e:
                log.error(f"Error loading control icon '{icon_filename}': {e}", exc_info=True)
                button.setText(tooltip[0]) # Fallback

        button.setIconSize(icon_size)
        button.setStyleSheet(style)
        button.setToolTip(tooltip)
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(slot)
        return button

    def _load_maximize_restore_icons(self):
        """Loads the icons used for the maximize/restore button."""
        self.maximize_icon = QIcon()
        self.restore_icon = QIcon()
        try:
            max_icon_path = graphics_directory_path('Maximize.png')
            res_icon_path = graphics_directory_path('Restore.png')
            log.info(f"TopBar: Loading Max/Res icons from: {max_icon_path}, {res_icon_path}")

            temp_max_icon = QIcon(max_icon_path)
            temp_res_icon = QIcon(res_icon_path)

            if temp_max_icon.isNull(): log.warning(f"Failed to load Maximize.png from {max_icon_path}")
            else: self.maximize_icon = temp_max_icon

            if temp_res_icon.isNull(): log.warning(f"Failed to load Restore.png from {res_icon_path}")
            else: self.restore_icon = temp_res_icon

        except Exception as e:
            log.error(f"Error loading Maximize/Restore icons: {e}", exc_info=True)

    def _update_maximize_button_icon(self):
        """Sets the correct icon (Maximize/Restore) and tooltip based on window state."""
        if not self.parent_window: return
        if self.parent_window.isMaximized():
            icon = self.restore_icon
            tooltip = "Restore Down"
            fallback = "[-]"
        else:
            icon = self.maximize_icon
            tooltip = "Maximize"
            fallback = "[+]"

        if not icon.isNull():
             self.maximize_button.setIcon(icon)
        else:
             self.maximize_button.setText(fallback) # Use text if icon failed
             log.warning(f"{tooltip} icon invalid or failed to load. Using text '{fallback}'.")
        self.maximize_button.setToolTip(tooltip)

    # --- Window Control Slots ---
    def _minimize_window(self):
        if self.parent_window: self.parent_window.showMinimized()

    def _toggle_maximize_window(self):
        if not self.parent_window: return
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()
        # Icon update is handled by the changeEvent in MainWindow

    def _close_window(self):
         if self.parent_window: self.parent_window.close()

    # --- Window Dragging Logic ---
    def mousePressEvent(self, event: QEvent):
        if self.parent_window and event.button() == Qt.LeftButton:
            # Check if the click is on the bar itself, not on a button
            widget_at_click = self.childAt(event.pos())
            # Allow dragging if click is on the bar background or the title label
            if widget_at_click is None or isinstance(widget_at_click, QLabel):
                # Check if window is maximized - dragging shouldn't work then
                if not self.parent_window.isMaximized():
                    self.offset = event.globalPos() - self.parent_window.frameGeometry().topLeft()
                    event.accept()
                else:
                    self.offset = None # Don't allow dragging maximized window
                    event.ignore()
            else: # Click was on a button
                self.offset = None
                event.ignore()
        else:
            self.offset = None
            event.ignore()

    def mouseMoveEvent(self, event: QEvent):
        if self.offset is not None and event.buttons() == Qt.LeftButton and self.parent_window:
            # Ensure we are not dragging a maximized window
            if not self.parent_window.isMaximized():
                new_pos = event.globalPos() - self.offset
                self.parent_window.move(new_pos)
                event.accept()
            else:
                 event.ignore() # Ignore move if maximized or offset is None
        else:
            event.ignore()

    def mouseReleaseEvent(self, event: QEvent):
        if event.button() == Qt.LeftButton:
            self.offset = None # Reset offset on release
            event.accept()
        else:
            event.ignore()


class MainWindow(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        log.info("Initializing MainWindow...")
        self._setup_window_properties()
        self._setup_ui()
        self._load_app_icon()
        log.info("MainWindow UI initialization complete.")

    def _setup_window_properties(self):
        """Sets window flags, attributes, and object name."""
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window) # Frameless, but acts as a window
        self.setAttribute(Qt.WA_TranslucentBackground, False) # Use False for solid background
        # Set object name for potential styling via main stylesheet if needed
        self.setObjectName("MainWindow")
        # Set window title (useful for taskbar identification)
        self.setWindowTitle(f"{ASSISTANT_NAME.capitalize()} AI")

    def _setup_ui(self):
        """Creates the main UI layout and widgets."""
        self._set_initial_geometry()
        self.setMinimumSize(800, 600) # Reasonable minimum size

        # Central widget setup
        central_widget = QWidget(self)
        # Apply base background color here, specific widgets can override
        central_widget.setStyleSheet("background-color: #121212;")
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0) # No margins, top bar and content fill space
        main_layout.setSpacing(0) # No spacing between top bar and content

        # Stacked widget for screens
        self.stacked_widget = QStackedWidget()
        initial_screen = InitialScreen(self.stacked_widget)
        message_screen = MessageScreen(self.stacked_widget)
        self.stacked_widget.addWidget(initial_screen) # Index 0
        self.stacked_widget.addWidget(message_screen) # Index 1

        # Custom top bar
        self.top_bar = CustomTopBar(self, self.stacked_widget)

        # Add top bar and stacked widget to main layout
        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.stacked_widget, 1) # Stacked widget takes remaining space

    def _set_initial_geometry(self):
        """Sets the initial size and position of the window, centered."""
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                 screens = QApplication.screens()
                 if screens: screen = screens[0]
            if screen:
                available_geo = screen.availableGeometry()
                log.info(f"Available screen geometry: {available_geo.width()}x{available_geo.height()} at ({available_geo.x()},{available_geo.y()})")
                # Calculate initial size as a percentage of available space, with min/max caps
                initial_width = max(800, min(1200, int(available_geo.width() * 0.65)))
                initial_height = max(600, min(900, int(available_geo.height() * 0.7)))
                # Center the window
                initial_x = available_geo.x() + (available_geo.width() - initial_width) // 2
                initial_y = available_geo.y() + (available_geo.height() - initial_height) // 2
                self.setGeometry(initial_x, initial_y, initial_width, initial_height)
                log.info(f"Set initial window geometry to: {initial_width}x{initial_height} at ({initial_x},{initial_y})")
            else:
                 log.error("No screens detected. Using default size/position (800x600 at 100,100).")
                 self.setGeometry(100, 100, 800, 600)
        except Exception as e:
            log.error(f"Could not get screen geometry for initial placement: {e}. Using defaults.", exc_info=True)
            self.setGeometry(100, 100, 800, 600)

    def _load_app_icon(self):
        """Loads and sets the application icon."""
        try:
            app_icon_path = graphics_directory_path("app_icon.png")
            log.info(f"MainWindow: Loading App icon from: {app_icon_path}")
            app_icon = QIcon(app_icon_path)
            if not app_icon.isNull():
                self.setWindowIcon(app_icon)
                log.info("Application icon set successfully.")
            else:
                log.warning(f"Application icon loaded but is invalid: {app_icon_path}")
                if not os.path.exists(app_icon_path):
                     log.error(f"Application icon file not found at physical path: {app_icon_path}")
        except Exception as e:
            log.error(f"Error setting application icon: {e}", exc_info=True)

    # --- Event Handlers ---
    def changeEvent(self, event: QEvent):
        """Handle window state changes (minimize, maximize, restore) to update buttons."""
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            # Check if the state change is relevant (maximized, minimized, normal)
            if self.windowState() & (Qt.WindowMaximized | Qt.WindowMinimized | Qt.WindowNoState):
                log.debug(f"Window state changed to: {self.windowState()}")
                if hasattr(self, 'top_bar') and self.top_bar:
                    # Use singleShot to ensure the update happens after the state change is fully processed
                    QTimer.singleShot(0, self.top_bar._update_maximize_button_icon)
                else:
                    log.warning("Window state changed but top_bar not found or not initialized yet.")

    def closeEvent(self, event: QEvent):
        """Handle the window close event (e.g., clicking the 'X' button)."""
        log.info("Close event triggered. Cleaning up timers...")
        try:
            # Stop timers in screens
            initial_screen = self.stacked_widget.widget(0)
            message_screen = self.stacked_widget.widget(1)

            if isinstance(initial_screen, InitialScreen):
                initial_screen.stop_timer()
            if isinstance(message_screen, MessageScreen):
                message_screen.stop_timers() # This should stop its own timer and the chat section's timer

        except Exception as e:
            log.error(f"Error stopping timers during close: {e}", exc_info=True)

        log.info("Cleanup finished. Allowing window to close.")
        super().closeEvent(event) # Proceed with closing


# --- Main Execution Function ---

def initialize_data_files():
    """Checks and initializes necessary data files on startup."""
    log.info("Initializing data files...")
    files_to_check = {
        MIC_DATA_FILE: "False",
        STATUS_DATA_FILE: "Initializing...",
        RESPONSES_DATA_FILE: "",
        GENERATED_IMAGE_DATA_FILE: "" # Clear/create image data file on startup
    }
    try:
        os.makedirs(TEMP_DIR_PATH, exist_ok=True) # Ensure directory exists first
        for filepath, default_content in files_to_check.items():
            # For GeneratedImage.data, always clear/create it
            if filepath == GENERATED_IMAGE_DATA_FILE:
                _safe_file_write(filepath, "") # Write empty string to clear or create
                log.info(f"Checked/Cleared {os.path.basename(filepath)}")
            else:
                # For others, use read which creates with default if missing
                _safe_file_read(filepath)
                log.info(f"Checked/Initialized {os.path.basename(filepath)}")
        log.info(f"Persistent data files checked/initialized in: {TEMP_DIR_PATH}")
    except Exception as e:
        log.critical(f"FATAL ERROR during data file initialization: {e}", exc_info=True)
        # Exit if critical file operations fail
        sys.exit(1)

def set_global_stylesheet(app: QApplication):
    """Applies a global stylesheet to the application."""
    app.setStyleSheet("""
        /* General Styles */
        QWidget {
            background-color: #121212;
            color: #f0f0f0;
            font-family: "Segoe UI", Arial, sans-serif; /* Added fallback fonts */
            font-size: 10pt; /* Base font size in points */
        }
        QMainWindow {
            border: 1px solid #383838; /* Add a border for frameless window if needed */
        }
        QLabel {
            background-color: transparent;
            color: #cccccc;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #f0f0f0;
            border: 1px solid #333333;
            border-radius: 5px;
            padding: 8px;
            font-size: 10pt; /* Consistent font size */
        }
        QPushButton {
            background-color: #333333;
            color: #f0f0f0;
            border: 1px solid #555555;
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 10pt;
            min-height: 28px; /* Minimum height */
        }
        QPushButton:hover {
            background-color: #444444;
            border-color: #777777;
        }
        QPushButton:pressed {
            background-color: #505050;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            color: #555555;
            border-color: #444444;
        }
        QPushButton:focus {
            /* Optional: Add a subtle focus indicator if desired, e.g.,
            border: 1px solid #55aaff;
            */
            outline: none; /* Remove default outline */
        }
        QToolTip {
            background-color: #282828;
            color: #f0f0f0;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
            opacity: 230; /* Semi-transparent */
        }

        /* Scrollbar Styling */
        QScrollBar:vertical {
            border: none;
            background: #1e1e1e; /* Match QTextEdit background */
            width: 10px; /* Slightly slimmer */
            margin: 0px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #666666;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            /* Remove arrows */
            border: none;
            background: none;
            height: 0px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }

        QScrollBar:horizontal {
            border: none;
            background: #1e1e1e;
            height: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal {
            background: #555555;
            min-width: 30px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #666666;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
            width: 0px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
    """)
    log.info("Global stylesheet applied.")


def graphical_user_interface():
    """Initializes and runs the PyQt application."""
    log.info("--- Starting GraphicalUserInterface ---")

    initialize_data_files()

    # --- Application Setup ---
    # Enable High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    log.info("High DPI scaling and pixmaps attributes set.")

    app = QApplication(sys.argv)

    set_global_stylesheet(app)

    log.info("Creating MainWindow instance...")
    window = MainWindow()
    log.info("Showing MainWindow...")
    window.show()

    log.info("Starting application event loop (app.exec_())...")
    exit_code = app.exec_()
    log.info(f"Application event loop finished. Exiting with code: {exit_code}")
    sys.exit(exit_code)

# --- Entry Point ---
if __name__ == "__main__":
    try:
        graphical_user_interface()
    except SystemExit as e:
        # Log normal exits initiated by sys.exit() or QApplication.quit()
        log.info(f"Application exited normally with code: {e.code}")
    except ImportError as e:
        # Catch missing critical imports like PyQt5 early
        log.critical(f"Missing required library: {e}. Please install it.", exc_info=True)
        # Optionally display a message box if GUI hasn't started
        # QtWidgets.QMessageBox.critical(None, "Error", f"Missing required library: {e}")
        sys.exit(1)
    except Exception as e:
        # Catch any other unexpected exceptions during setup or runtime
        log.critical(f"FATAL UNHANDLED ERROR in GUI execution: {e}", exc_info=True)
        # Optionally display a message box
        # QtWidgets.QMessageBox.critical(None, "Fatal Error", f"An unexpected error occurred:\n{e}")
        # Add input prompt only if not running bundled/frozen
        if not getattr(sys, 'frozen', False):
             input("Press Enter to exit...") # Prevent console closing immediately on error in dev
        sys.exit(1) # Exit with error code

