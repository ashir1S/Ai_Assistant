# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QStackedWidget,
                             QWidget, QLineEdit, QGridLayout, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QSizePolicy, QFrame, QDesktopWidget) # Added QFrame, QDesktopWidget
from PyQt5.QtGui import (QIcon, QPainter, QMovie, QColor, QTextCharFormat, QFont,
                         QPixmap, QTextBlockFormat, QScreen, QTextCursor) # Added QTextCursor
from PyQt5.QtCore import Qt, QSize, QTimer, QEvent, QPoint, QRect # Added QEvent, QPoint, QRect
from dotenv import dotenv_values
import sys
import os
import platform # Added for better path handling
import traceback # For detailed error logging

# --- Configuration and Globals ---
try:
    # Determine script directory robustly
    if getattr(sys, 'frozen', False):
        # If running as a bundled executable (e.g., PyInstaller)
        script_dir = os.path.dirname(sys.executable)
    else:
        # If running as a standard Python script
        script_dir = os.path.dirname(os.path.abspath(__file__))

    env_path = os.path.join(script_dir, '..', '.env') # Check one level up first
    if not os.path.exists(env_path):
        env_path = os.path.join(script_dir, '.env') # Check in the script dir

    if os.path.exists(env_path):
        env_vars = dotenv_values(env_path)
        Assistantname = env_vars.get("Assistantname", "Assistant")
        print(f"Loaded Assistantname '{Assistantname}' from {env_path}")
    else:
        print(f"Warning: .env file not found at {os.path.join(script_dir, '..', '.env')} or {os.path.join(script_dir, '.env')}. Using default values.")
        Assistantname = "Assistant"

except Exception as e:
    print(f"Warning: Could not load .env file. Using default values. Error: {e}")
    Assistantname = "Assistant"

# Use the same script_dir logic for frontend_dir if GUI.py is the entry point
frontend_dir = script_dir # os.path.dirname(os.path.abspath(__file__))
TempDirPath = os.path.join(frontend_dir, "Files")
GraphicsDirPath = os.path.join(frontend_dir, "Graphics")

print(f"Script Directory: {script_dir}")
print(f"Frontend Directory: {frontend_dir}")
print(f"Graphics Directory Path: {GraphicsDirPath}")
print(f"Temp Directory Path: {TempDirPath}")


os.makedirs(TempDirPath, exist_ok=True)
os.makedirs(GraphicsDirPath, exist_ok=True)

old_chat_message = ""

# --- Helper Functions ---

def AnswerModifier(Answer):
    """Removes empty lines from the answer string."""
    if not Answer:
        return ""
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def QueryModifier(Query):
    """Formats the query: lowercase, strip, capitalize, add period if question."""
    if not Query:
        return ""
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = [ "how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you","what's", "where's", "how's"]

    is_question = any(new_query.startswith(word + " ") for word in question_words)

    if is_question:
        if query_words and query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        elif not new_query.endswith('.'):
            new_query += "."

    # Capitalize the first letter
    if new_query:
        new_query = new_query[0].upper() + new_query[1:]
    return new_query # Return modified query

def _safe_file_write(filepath, content):
    """Safely writes content to a file."""
    try:
        with open(filepath, "w", encoding='utf-8') as file:
            file.write(content)
        # print(f"Successfully wrote to {filepath}") # Optional: uncomment for verbose logging
    except IOError as e:
        print(f"Error writing to file {filepath}: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"Unexpected error writing to file {filepath}: {e}")
        traceback.print_exc()


def _safe_file_read(filepath):
    """Safely reads content from a file, creating it with defaults if missing."""
    try:
        filename = os.path.basename(filepath) # Get filename for default logic
        if not os.path.exists(filepath):
            default_content = ""
            if "Mic.data" == filename:
                default_content = "False"
            elif "Status.data" == filename:
                default_content = "Initializing..."
            elif "Responses.data" == filename:
                default_content = "" # Default responses is empty

            print(f"File '{filepath}' not found. Creating with default content: '{default_content}'")
            _safe_file_write(filepath, default_content)
            return default_content # Return the default immediately

        # If file exists, read it
        with open(filepath, "r", encoding='utf-8') as file:
            content = file.read()
            # print(f"Successfully read from {filepath}") # Optional: uncomment for verbose logging
            return content
    except IOError as e:
        print(f"IOError reading from file {filepath}: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"Unexpected error reading file {filepath}: {e}")
        traceback.print_exc()

    # Fallback return if reading failed after file existence check
    print(f"Warning: Failed to read existing file {filepath}. Returning default.")
    filename = os.path.basename(filepath)
    if "Mic.data" == filename: return "False"
    if "Status.data" == filename: return "Initializing..."
    return ""

def SetMicrophoneStatus(Command):
    """Sets the microphone status ('True' or 'False') in Mic.data."""
    _safe_file_write(os.path.join(TempDirPath, "Mic.data"), str(Command))

def GetMicrophoneStatus():
    """Gets the microphone status from Mic.data."""
    return _safe_file_read(os.path.join(TempDirPath, "Mic.data"))

def SetAssistantStatus(Status):
    """Sets the assistant's current status text in Status.data."""
    _safe_file_write(os.path.join(TempDirPath, "Status.data"), Status)

def GetAssistantStatus():
    """Gets the assistant's current status text from Status.data."""
    return _safe_file_read(os.path.join(TempDirPath, "Status.data"))

def MicButtonInitialed():
    """Action when mic button is toggled OFF (set to False)."""
    SetMicrophoneStatus("False")
    print("Mic Status Set: False")

def MicButtonClosed():
    """Action when mic button is toggled ON (set to True)."""
    SetMicrophoneStatus("True")
    print("Mic Status Set: True")

def GraphicsDirectoryPath(Filename):
    """Returns the full path for a graphics file."""
    return os.path.join(GraphicsDirPath, Filename)

def TempDirectoryPath(Filename):
    """Returns the full path for a temporary data file."""
    return os.path.join(TempDirPath, Filename)

def ShowTextToScreen(Text):
    """Writes text to the Responses.data file for display."""
    # Apply QueryModifier if you want user input formatted before display/processing
    # modified_text = QueryModifier(Text) # Example: Format user input here if needed
    # _safe_file_write(TempDirectoryPath('Responses.data'), modified_text)
    # Or just write the raw text if it's assistant output
    _safe_file_write(TempDirectoryPath('Responses.data'), Text)


# --- GUI Classes ---

class ChatSection(QWidget):
    """Widget displaying the chat messages and assistant status/animation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        print("Initializing ChatSection...")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.chat_text_edit = QTextEdit()
        self.chat_text_edit.setReadOnly(True)
        # Allow text selection but not editing
        self.chat_text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.chat_text_edit.setFrameStyle(QFrame.NoFrame) # No border around text edit

        font = QFont()
        font.setPointSize(14) # Set chat font size
        self.chat_text_edit.setFont(font)

        # --- Bottom section layout (Status Label and GIF) ---
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 10, 0, 0) # Top margin for spacing
        bottom_layout.setSpacing(15)

        self.label = QLabel("Status: Initializing...")
        self.label.setStyleSheet("color: #999999; font-size:16px; border: none; background-color: transparent;")
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) # Align text left and vertically centered
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred) # Allow label to expand horizontally

        self.gif_label = QLabel()
        self.gif_label.setStyleSheet("border: none; background-color: transparent;")
        self.movie = None # Hold reference to the movie object

        try:
            gif_path = GraphicsDirectoryPath('Jarvis.gif')
            print(f"--- ChatSection: Attempting to load GIF from: {gif_path}")

            if not os.path.exists(gif_path):
                print(f"--- ChatSection: ERROR - GIF file not found at {gif_path}")
                self.gif_label.setText("(GIF Not Found)")
            else:
                print(f"--- ChatSection: GIF file exists. Creating QMovie object...")
                self.movie = QMovie(gif_path) # Assign to self.movie

                if self.movie.isValid():
                    print(f"--- ChatSection: QMovie created successfully. GIF format: {self.movie.format().data().decode()}")
                    max_gif_size_W = 160 # Smaller GIF for chat section
                    max_gif_size_H = 90
                    print(f"--- ChatSection: Max GIF dimensions: {max_gif_size_W}x{max_gif_size_H}")

                    # Calculate the target size QSize object first
                    target_size = QSize(max_gif_size_W, max_gif_size_H)

                    # Scale the target size using QSize.scaled (FIXED: removed SmoothTransformation)
                    print(f"--- ChatSection: Scaling target QSize ({target_size.width()}x{target_size.height()}) keeping aspect ratio...")
                    scaled_target_size = target_size.scaled(max_gif_size_W, max_gif_size_H, Qt.KeepAspectRatio)
                    print(f"--- ChatSection: Calculated scaled QSize: {scaled_target_size.width()}x{scaled_target_size.height()}")

                    # Set the calculated scaled size for the QMovie object
                    print(f"--- ChatSection: Setting scaled size on QMovie...")
                    self.movie.setScaledSize(scaled_target_size)

                    # Assign the movie to the label
                    print(f"--- ChatSection: Assigning QMovie to QLabel...")
                    self.gif_label.setMovie(self.movie)
                    self.gif_label.setFixedSize(scaled_target_size) # Set fixed size for layout stability

                    # Start the animation
                    print("--- ChatSection: Starting movie...")
                    self.movie.start()
                    print(f"--- ChatSection: Movie state after start: {self.movie.state()} (2 means Running)")
                    if self.movie.state() != QMovie.Running:
                         print(f"--- ChatSection: WARNING - Movie did not start correctly! Error: {self.movie.lastErrorString()}")

                else:
                    # QMovie object was created but the GIF data is invalid/unsupported
                    self.gif_label.setText("(GIF Error)")
                    err_code = self.movie.lastError()
                    err_str = self.movie.lastErrorString()
                    print(f"--- ChatSection: ERROR - QMovie is invalid after creation.")
                    print(f"--- ChatSection:   File: {gif_path}")
                    print(f"--- ChatSection:   Error Code: {err_code}")
                    print(f"--- ChatSection:   Error String: {err_str}")
        except Exception as e:
            self.gif_label.setText("(GIF Load Exception)")
            print(f"--- ChatSection: EXCEPTION during GIF loading/processing: {e}")
            traceback.print_exc() # Print full traceback for exceptions

        self.gif_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # Align GIF right and vertically centered

        bottom_layout.addWidget(self.label)    # Status label on the left
        # bottom_layout.addStretch(1)           # Pushes GIF to the right (optional)
        bottom_layout.addWidget(self.gif_label) # GIF label on the right

        layout.addWidget(self.chat_text_edit, 1) # Text edit takes expanding space (stretch factor 1)
        layout.addLayout(bottom_layout)          # Add the bottom layout

        self.setStyleSheet("background-color: #121212;") # Background for the whole ChatSection

        # Style the text edit area including scrollbars
        self.chat_text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; /* Darker background for text area */
                color: #f0f0f0; /* Light text color */
                border: none; /* No border around text edit */
                padding: 10px; /* Padding inside text area */
            }
            QScrollBar:vertical {
                border: none;
                background: #1e1e1e; /* Match text edit background */
                width: 12px; /* Width of the scrollbar */
                margin: 0px 0px 0px 0px; /* No margins */
            }
            QScrollBar::handle:vertical {
                background: #555555; /* Scrollbar handle color */
                min-height: 30px; /* Minimum handle height */
                border-radius: 6px; /* Rounded corners */
            }
            QScrollBar::handle:vertical:hover {
                background: #666666; /* Handle color on hover */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none; /* No background for top/bottom buttons */
                height: 0px; /* Hide top/bottom buttons */
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none; /* No background for the page area */
            }
        """)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.loadMessages)
        self.timer.timeout.connect(self.updateStatusLabel)
        self.timer.start(200) # Update interval in milliseconds
        print("ChatSection initialization complete.")


    def loadMessages(self):
        """Loads messages from Responses.data and updates the chat display."""
        global old_chat_message
        try:
            # Ensure the file path is correct
            response_file_path = TempDirectoryPath('Responses.data')
            messages = _safe_file_read(response_file_path)

            if messages is not None and messages != old_chat_message:
                # Apply AnswerModifier to clean up the response before displaying
                cleaned_message = AnswerModifier(messages)

                if cleaned_message: # Only add if there's content after cleaning
                    # print(f"ChatSection: New message detected, adding to display.") # Optional debug
                    self.addMessage(message=cleaned_message, color='#f0f0f0') # Use light color for assistant messages
                    old_chat_message = messages # Update the old message *after* processing
                elif messages == "" and old_chat_message != "":
                    # Handle case where Responses.data is cleared
                    # self.chat_text_edit.clear() # Option 1: Clear display entirely
                    print("ChatSection: Responses.data cleared, updating internal state.") # Option 2: Just update state
                    old_chat_message = messages
                # else: # message is None or hasn't changed
                    # print(f"ChatSection: No message change detected.") # Optional debug

        except Exception as e:
            print(f"Error in ChatSection loadMessages: {e}")
            traceback.print_exc() # Print full traceback

    def updateStatusLabel(self):
        """Updates the status label by reading from Status.data."""
        try:
            status_text = GetAssistantStatus()
            current_text = self.label.text() # Get the current text *including* "Status: "
            display_text = f"Status: {status_text or 'Idle'}" # Use 'Idle' if status is empty

            if current_text != display_text:
                # print(f"ChatSection: Updating status label to: {display_text}") # Optional debug
                self.label.setText(display_text)
        except Exception as e:
            print(f"Error in ChatSection updateStatusLabel: {e}")
            traceback.print_exc()

    def addMessage(self, message, color):
        """Adds a formatted message to the chat display."""
        try:
            cursor = self.chat_text_edit.textCursor()
            cursor.movePosition(QTextCursor.End) # Go to the very end

            # Check if the current block is empty or if it's the start of the document
            is_empty_doc = self.chat_text_edit.document().isEmpty()
            if not is_empty_doc:
                 # Insert a new block (paragraph) only if not the first message
                 cursor.insertBlock()

            # --- Formatting ---
            char_format = QTextCharFormat()
            char_format.setForeground(QColor(color))
            # Optionally set font size again here if needed per message
            font = QFont(); font.setPointSize(14); char_format.setFont(font)

            block_format = QTextBlockFormat()
            block_format.setTopMargin(6)    # Space above the block
            block_format.setBottomMargin(6) # Space below the block
            block_format.setLeftMargin(10)  # Indentation from left
            block_format.setRightMargin(10) # Indentation from right

            cursor.setBlockFormat(block_format) # Apply block spacing/margins
            cursor.setCharFormat(char_format)   # Apply text color/font

            cursor.insertText(message) # Insert the actual message text

            # Scroll to the bottom to ensure the latest message is visible
            self.chat_text_edit.ensureCursorVisible()
        except Exception as e:
            print(f"Error in ChatSection addMessage: {e}")
            traceback.print_exc() # Print full traceback


class InitialScreen(QWidget):
    """The initial screen with a large GIF and microphone toggle."""
    def __init__(self, parent=None):
        super().__init__(parent)
        print("Initializing InitialScreen...")
        try:
            screen = QApplication.primaryScreen()
            if not screen:
                print("Warning: QApplication.primaryScreen() returned None. Using first available screen.")
                screens = QApplication.screens()
                if screens:
                    screen = screens[0]
                else:
                    # Absolute fallback if no screens are detected
                    print("ERROR: No screens detected by QApplication. Using default geometry.")
                    screen_geometry = QRect(0, 0, 1024, 768)
            if screen: # Only get geometry if screen is valid
                screen_geometry = screen.geometry() # Use geometry() for full screen size
                print(f"Detected screen geometry: {screen_geometry.width()}x{screen_geometry.height()}")

        except Exception as e:
             print(f"Warning: Could not get screen geometry using QScreen ({e}). Falling back to QDesktopWidget.")
             traceback.print_exc()
             try:
                 desktop = QDesktopWidget()
                 screen_geometry = desktop.screenGeometry() # Deprecated but fallback
                 print(f"Detected screen geometry (QDesktopWidget): {screen_geometry.width()}x{screen_geometry.height()}")
             except Exception as e_desk:
                 print(f"ERROR: Failed to get screen geometry via QDesktopWidget either ({e_desk}). Using defaults.")
                 traceback.print_exc()
                 screen_geometry = QRect(0, 0, 1024, 768) # Default fallback

        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(20, 20, 20, 20) # Generous margins
        content_layout.setSpacing(20) # Space between elements

        # --- Large GIF Label ---
        gif_label = QLabel()
        gif_label.setStyleSheet("border: none; background-color: transparent;")
        self.initial_movie = None # Hold reference

        try:
            gif_path = GraphicsDirectoryPath('Jarvis.gif')
            print(f"--- InitialScreen: Attempting to load GIF from: {gif_path}")
            if not os.path.exists(gif_path):
                 print(f"--- InitialScreen: ERROR - GIF file not found at {gif_path}")
                 gif_label.setText("(GIF Not Found)")
            else:
                print(f"--- InitialScreen: GIF file exists. Creating QMovie object...")
                self.initial_movie = QMovie(gif_path) # Assign to self.initial_movie

                if self.initial_movie.isValid():
                    print(f"--- InitialScreen: QMovie created successfully. Format: {self.initial_movie.format().data().decode()}")
                    # --- Dynamic Scaling based on Screen Size ---
                    gif_aspect_ratio = 16 / 9 # Assume 16:9, adjust if needed
                    # Use a percentage of screen width/height, but cap reasonably
                    max_gif_width = min(screen_width * 0.7, 1000) # 70% of width, max 1000px
                    max_gif_height = min(screen_height * 0.5, 600) # 50% of height, max 600px

                    # Calculate initial scaled size based on width limit
                    scaled_width = int(max_gif_width)
                    scaled_height = int(max_gif_width / gif_aspect_ratio)

                    # If calculated height exceeds max height, recalculate based on height limit
                    if scaled_height > max_gif_height:
                        scaled_height = int(max_gif_height)
                        scaled_width = int(max_gif_height * gif_aspect_ratio)

                    scaled_size = QSize(scaled_width, scaled_height)
                    print(f"--- InitialScreen: Calculated scaled GIF size: {scaled_size.width()}x{scaled_size.height()}")

                    # Set the scaled size for the QMovie object
                    print(f"--- InitialScreen: Setting scaled size on QMovie...")
                    self.initial_movie.setScaledSize(scaled_size)

                    print(f"--- InitialScreen: Assigning QMovie to QLabel...")
                    gif_label.setMovie(self.initial_movie)

                    print("--- InitialScreen: Starting movie...")
                    self.initial_movie.start()
                    print(f"--- InitialScreen: Movie state after start: {self.initial_movie.state()}")
                    if self.initial_movie.state() != QMovie.Running:
                         print(f"--- InitialScreen: WARNING - Movie did not start correctly! Error: {self.initial_movie.lastErrorString()}")

                else:
                    gif_label.setText("(GIF Error)")
                    err_code = self.initial_movie.lastError()
                    err_str = self.initial_movie.lastErrorString()
                    print(f"--- InitialScreen: ERROR - QMovie is invalid after creation.")
                    print(f"--- InitialScreen:   File: {gif_path}")
                    print(f"--- InitialScreen:   Error Code: {err_code}")
                    print(f"--- InitialScreen:   Error String: {err_str}")

        except Exception as e:
            gif_label.setText("(GIF Load Exception)")
            print(f"--- InitialScreen: EXCEPTION during GIF loading/processing: {e}")
            traceback.print_exc()

        gif_label.setAlignment(Qt.AlignCenter)
        # Allow GIF to expand but also have a minimum size
        gif_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        gif_label.setMinimumSize(200, 112) # Minimum size based on aspect ratio

        # --- Microphone Icon Label ---
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(80, 80) # Fixed size for the clickable area
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("border: none; background-color: transparent;")
        self.icon_label.setCursor(Qt.PointingHandCursor) # Indicate it's clickable

        # --- Status Label ---
        self.label = QLabel("Status: Initializing...")
        self.label.setStyleSheet("color: #cccccc; font-size: 18px; border: none; background-color: transparent; qproperty-alignment: 'AlignCenter';") # Use property for alignment
        # self.label.setAlignment(Qt.AlignCenter) # Alternative alignment setting

        # --- Layout Assembly ---
        content_layout.addStretch(1) # Push content towards center vertically
        content_layout.addWidget(gif_label) # Add GIF (already centered)
        content_layout.addWidget(self.label) # Add status label (already centered)
        content_layout.addWidget(self.icon_label, alignment=Qt.AlignCenter) # Add icon, explicitly center horizontally
        content_layout.addStretch(1) # Push content towards center vertically

        # --- Mic Icon Setup ---
        self.mic_on_pixmap = None
        self.mic_off_pixmap = None
        try:
            mic_on_path = GraphicsDirectoryPath('Mic_on.png')
            mic_off_path = GraphicsDirectoryPath('Mic_off.png')
            print(f"Loading Mic On icon from: {mic_on_path}")
            print(f"Loading Mic Off icon from: {mic_off_path}")

            temp_mic_on = QPixmap(mic_on_path)
            temp_mic_off = QPixmap(mic_off_path)

            if temp_mic_on.isNull():
                print(f"ERROR: Failed to load Mic_on.png from {mic_on_path}")
                raise ValueError("Mic_on.png failed to load or is invalid.")
            if temp_mic_off.isNull():
                print(f"ERROR: Failed to load Mic_off.png from {mic_off_path}")
                raise ValueError("Mic_off.png failed to load or is invalid.")

            icon_display_size = 60 # Size to display the icon within the 80x80 label
            print(f"Scaling mic icons to {icon_display_size}x{icon_display_size}")
            # Use SmoothTransformation for potentially better quality scaling of static images
            self.mic_on_pixmap = temp_mic_on.scaled(icon_display_size, icon_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.mic_off_pixmap = temp_mic_off.scaled(icon_display_size, icon_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            print("Mic icons loaded and scaled successfully.")

        except Exception as e:
            print(f"ERROR loading mic icons: {e}")
            traceback.print_exc()
            print("Using fallback colored squares for mic icons.")
            fallback_size = 60
            self.mic_on_pixmap = QPixmap(fallback_size, fallback_size)
            self.mic_on_pixmap.fill(Qt.darkGreen) # Use dark green for 'on'
            self.mic_off_pixmap = QPixmap(fallback_size, fallback_size)
            self.mic_off_pixmap.fill(Qt.darkRed) # Use dark red for 'off'

        # Set initial state based on file
        initial_mic_status = GetMicrophoneStatus()
        # Normalize the status read from file
        self.toggled = (str(initial_mic_status).strip().lower() == "true")
        print(f"Initial mic status from file: '{initial_mic_status}', Toggled state set to: {self.toggled}")
        self.update_icon() # Set the correct initial icon

        # Connect the click event directly to the label
        self.icon_label.mousePressEvent = self.toggle_icon

        self.setStyleSheet("background-color: #121212;") # Background for the whole InitialScreen

        # Timer for updating the status label
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateStatusLabel)
        self.timer.start(200) # Update interval
        print("InitialScreen initialization complete.")

    def updateStatusLabel(self):
        """Updates the status label by reading from Status.data."""
        try:
            status_text = GetAssistantStatus()
            current_text = self.label.text()
            display_text = f"Status: {status_text or 'Idle'}"
            if current_text != display_text:
                # print(f"InitialScreen: Updating status label to: {display_text}") # Optional debug
                self.label.setText(display_text)
        except Exception as e:
            print(f"Error in InitialScreen updateStatusLabel: {e}")
            traceback.print_exc()


    def update_icon(self):
        """Updates the mic icon label based on the self.toggled state."""
        if self.toggled:
            if self.mic_on_pixmap:
                self.icon_label.setPixmap(self.mic_on_pixmap)
            else:
                self.icon_label.setText("MIC ON") # Fallback text if pixmap failed
        else:
            if self.mic_off_pixmap:
                self.icon_label.setPixmap(self.mic_off_pixmap)
            else:
                self.icon_label.setText("MIC OFF") # Fallback text if pixmap failed

    def toggle_icon(self, event):
        """Handles clicks on the mic icon label."""
        # Ensure it's a left-click event
        if event.button() == Qt.LeftButton:
            self.toggled = not self.toggled # Flip the state
            print(f"Mic icon clicked. New toggled state: {self.toggled}")
            if self.toggled:
                MicButtonClosed() # Call function to set status to "True"
            else:
                MicButtonInitialed() # Call function to set status to "False"
            self.update_icon() # Update the visual icon
            event.accept() # Indicate event was handled
        else:
            event.ignore() # Ignore other mouse buttons


class MessageScreen(QWidget):
    """Screen dedicated to showing the ChatSection."""
    def __init__(self, parent=None):
        super().__init__(parent)
        print("Initializing MessageScreen...")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0) # No margins around the chat section
        layout.setSpacing(0) # No spacing
        self.chat_section = ChatSection(self) # Create and embed the ChatSection
        layout.addWidget(self.chat_section)
        # Background is handled by ChatSection, but set base anyway
        self.setStyleSheet("background-color: #121212;")
        print("MessageScreen initialization complete.")


class CustomTopBar(QWidget):
    """Custom top bar with title, navigation, and window controls."""
    def __init__(self, parent, stacked_widget):
        super().__init__(parent)
        print("Initializing CustomTopBar...")
        self.parent_window = parent # Reference to the main window
        self.stacked_widget = stacked_widget # Reference to the page switcher
        self.offset = None # For window dragging
        self.initUI()

    def initUI(self):
        self.setFixedHeight(50) # Standard height for the top bar
        self.setStyleSheet("""
            QWidget {
                background-color: #212121; /* Slightly lighter than main background */
                border-bottom: 1px solid #333333; /* Subtle separator line */
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0) # Left/Right margins, no top/bottom
        layout.setSpacing(10) # Spacing between elements in the bar

        # --- Title ---
        title_label = QLabel(f" {str(Assistantname).capitalize()} AI ") # Added spaces for padding
        title_label.setStyleSheet("""
            QLabel {
                color: #55aaff; /* Bright blue for title */
                font-size: 19px;
                font-weight: bold;
                padding-left: 5px;
                background-color: transparent; /* Ensure no background override */
                border: none; /* Ensure no border override */
            }
        """)

        # --- Navigation Buttons ---
        button_style = """
            QPushButton {
                background-color: transparent;
                color: #f0f0f0;
                border: none;
                padding: 8px 12px; /* Padding around text/icon */
                border-radius: 5px;
                font-size: 15px; /* Slightly smaller font for nav */
                min-height: 30px; /* Ensure clickable height */
                text-align: left; /* Align text/icon left */
            }
            QPushButton:hover {
                background-color: #333333; /* Darker gray on hover */
            }
            QPushButton:pressed {
                background-color: #444444; /* Even darker when pressed */
            }
            QPushButton:focus {
                outline: none; /* Remove focus rectangle */
            }
        """
        icon_size = QSize(30, 30) # Slightly smaller icons for nav

        home_button = QPushButton(" Home")
        try:
            home_icon_path = GraphicsDirectoryPath("Home.png")
            home_icon = QIcon(home_icon_path)
            if not home_icon.isNull():
                 home_button.setIcon(home_icon)
                 print(f"Loaded Home icon: {home_icon_path}")
            else: print(f"Warning: Home.png icon is invalid or not found at {home_icon_path}")
        except Exception as e: print(f"Failed to load Home.png: {e}")
        home_button.setIconSize(icon_size)
        home_button.setStyleSheet(button_style)
        home_button.setCursor(Qt.PointingHandCursor)
        home_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0)) # Switch to page 0

        message_button = QPushButton(" Chat")
        try:
            chat_icon_path = GraphicsDirectoryPath("Chats.png")
            message_icon = QIcon(chat_icon_path)
            if not message_icon.isNull():
                 message_button.setIcon(message_icon)
                 print(f"Loaded Chat icon: {chat_icon_path}")
            else: print(f"Warning: Chats.png icon is invalid or not found at {chat_icon_path}")
        except Exception as e: print(f"Failed to load Chats.png: {e}")
        message_button.setIconSize(icon_size)
        message_button.setStyleSheet(button_style)
        message_button.setCursor(Qt.PointingHandCursor)
        message_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Switch to page 1

        # --- Window Control Buttons ---
        control_button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                border-radius: 5px;
                min-width: 36px; max-width: 36px; /* Fixed width */
                min-height: 30px; max-height: 30px; /* Fixed height */
            }
            QPushButton:hover {
                background-color: #333333;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
            QPushButton:focus {
                outline: none;
            }
        """
        control_icon_size = QSize(23, 23) # Smaller icons for controls

        minimize_button = QPushButton()
        try:
            min_icon_path = GraphicsDirectoryPath('Minimize2.png')
            minimize_icon = QIcon(min_icon_path)
            if not minimize_icon.isNull():
                 minimize_button.setIcon(minimize_icon)
                 print(f"Loaded Minimize icon: {min_icon_path}")
            else: print(f"Warning: Minimize2.png icon is invalid or not found at {min_icon_path}")
        except Exception as e: print(f"Failed to load Minimize2.png: {e}")
        minimize_button.setIconSize(control_icon_size)
        minimize_button.setStyleSheet(control_button_style)
        minimize_button.setToolTip("Minimize")
        minimize_button.setCursor(Qt.PointingHandCursor)
        minimize_button.clicked.connect(self.minimizeWindow)

        # Maximize/Restore Button Setup (Loads BOTH icons)
        self.maximize_button = QPushButton()
        self.maximize_icon = QIcon()
        self.restore_icon = QIcon()
        try:
            max_icon_path = GraphicsDirectoryPath('Maximize.png')
            # *** USE DEDICATED RESTORE ICON ***
            res_icon_path = GraphicsDirectoryPath('Restore.png') # <-- Changed filename
            print(f"Loading Maximize icon: {max_icon_path}")
            print(f"Loading Restore icon: {res_icon_path}")

            temp_max_icon = QIcon(max_icon_path)
            temp_res_icon = QIcon(res_icon_path) # <-- Load Restore.png

            if not temp_max_icon.isNull(): self.maximize_icon = temp_max_icon
            else: print(f"Warning: Maximize.png icon is invalid or not found at {max_icon_path}")

            if not temp_res_icon.isNull(): self.restore_icon = temp_res_icon
            else: print(f"Warning: Restore.png icon is invalid or not found at {res_icon_path}") # <-- Updated warning

        except Exception as e: print(f"Error loading Maximize/Restore icons: {e}")

        # Set initial icon/tooltip later using updateMaximizeButtonIcon
        self.maximize_button.setIconSize(control_icon_size)
        self.maximize_button.setStyleSheet(control_button_style)
        self.maximize_button.setCursor(Qt.PointingHandCursor)
        self.maximize_button.clicked.connect(self.maximizeWindow)

        close_button = QPushButton()
        try:
            close_icon_path = GraphicsDirectoryPath('Close.png')
            close_icon = QIcon(close_icon_path)
            if not close_icon.isNull():
                 close_button.setIcon(close_icon)
                 print(f"Loaded Close icon: {close_icon_path}")
            else: print(f"Warning: Close.png icon is invalid or not found at {close_icon_path}")
        except Exception as e: print(f"Failed to load Close.png: {e}")
        close_button.setIconSize(control_icon_size)
        # Special hover/pressed style for close button
        close_button.setStyleSheet(control_button_style +
            " QPushButton:hover { background-color: #E81123; /* Red on hover */ }"
            " QPushButton:pressed { background-color: #F1707A; /* Lighter red when pressed */ }")
        close_button.setToolTip("Close")
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.clicked.connect(self.closeWindow)

        # --- Assemble Top Bar Layout ---
        layout.addWidget(title_label)
        layout.addStretch(1) # Push navigation buttons away from title
        layout.addWidget(home_button)
        layout.addWidget(message_button)
        layout.addStretch(2) # Push window controls to the far right
        layout.addWidget(minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(close_button)

        # Set the correct initial icon for maximize/restore button
        QTimer.singleShot(0, self.updateMaximizeButtonIcon)
        print("CustomTopBar initialization complete.")


    def updateMaximizeButtonIcon(self):
        """Sets the correct icon (Maximize/Restore) and tooltip based on window state."""
        if not self.parent_window: return # Should not happen, but safe check

        if self.parent_window.isMaximized():
            # Set Restore icon and tooltip
            if not self.restore_icon.isNull():
                self.maximize_button.setIcon(self.restore_icon)
            else:
                self.maximize_button.setText("[-]") # Fallback text
                print("Warning: Restore icon is invalid, using text fallback '[-]'")
            self.maximize_button.setToolTip("Restore Down")
        else:
            # Set Maximize icon and tooltip
            if not self.maximize_icon.isNull():
                self.maximize_button.setIcon(self.maximize_icon)
            else:
                self.maximize_button.setText("[+]") # Fallback text
                print("Warning: Maximize icon is invalid, using text fallback '[+]'")
            self.maximize_button.setToolTip("Maximize")

    def minimizeWindow(self):
        if self.parent_window:
            print("Minimizing window.")
            self.parent_window.showMinimized()

    def maximizeWindow(self):
        if not self.parent_window: return
        if self.parent_window.isMaximized():
            print("Restoring window.")
            self.parent_window.showNormal()
        else:
            print("Maximizing window.")
            self.parent_window.showMaximized()
        # Note: The icon update happens automatically via the changeEvent -> updateMaximizeButtonIcon

    def closeWindow(self):
         if self.parent_window:
             print("Closing window.")
             self.parent_window.close() # Graceful close, triggers closeEvent

    # --- Window Dragging Logic ---
    def mousePressEvent(self, event):
        # Check if the click is on the bar itself (not on a child widget like a button)
        # and it's the left mouse button.
        if self.parent_window and event.button() == Qt.LeftButton:
            # Check if the click occurred directly on the CustomTopBar widget
            widget_at_click = self.childAt(event.pos())
            if widget_at_click is None: # Click was on the bar background
                # Store the offset between the global cursor position and window's top-left corner
                self.offset = event.globalPos() - self.parent_window.frameGeometry().topLeft()
                print(f"Mouse press on top bar detected at {event.pos()}, starting drag.")
                event.accept() # We handled this event
            else:
                # Click was on a button or other child widget, ignore for dragging
                # print(f"Mouse press on child widget {widget_at_click}, ignoring drag.")
                self.offset = None
                event.ignore() # Let the child widget handle it
        else:
            # Not a left click, or no parent window
            self.offset = None
            event.ignore()

    def mouseMoveEvent(self, event):
        # Check if dragging started (offset is set), left button is held, and parent exists
        if self.offset is not None and event.buttons() == Qt.LeftButton and self.parent_window:
            # Only move if the window is not maximized
            if not self.parent_window.isMaximized():
                # Calculate new window top-left position
                new_pos = event.globalPos() - self.offset
                # Move the main window
                self.parent_window.move(new_pos)
                # print(f"Dragging window to {new_pos}") # Verbose logging
                event.accept()
            else:
                # Don't drag if maximized
                event.ignore()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        # Reset offset when the left mouse button is released
        if event.button() == Qt.LeftButton:
            if self.offset is not None:
                 print("Mouse release, ending drag.")
            self.offset = None
            event.accept()
        else:
            event.ignore()


class MainWindow(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        print("Initializing MainWindow...")
        # --- Frameless Window Setup ---
        # Essential flags for a custom-drawn window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window) # Base flags # Base flags
        # Allows transparency if needed, but main widget background should be opaque
        self.setAttribute(Qt.WA_TranslucentBackground, False) # Set to False if main widget fills everything
        self.setObjectName("MainWindow") # For styling specific to this window

        self.initUI()

    def initUI(self):
        # --- Determine Initial Window Size and Position ---
        try:
            screen = QApplication.primaryScreen()
            if not screen: screen = QApplication.screens()[0]
            # Use availableGeometry to avoid placing window under taskbars etc.
            screen_geometry = screen.availableGeometry()
            print(f"Available screen geometry: {screen_geometry.width()}x{screen_geometry.height()} at ({screen_geometry.x()},{screen_geometry.y()})")
        except Exception as e:
            print(f"Warning: Could not get screen geometry ({e}). Falling back to defaults.")
            traceback.print_exc()
            # Fallback geometry if screen detection fails
            screen_geometry = QRect(0, 0, 1280, 720) # A reasonable default available size

        # Set initial size relative to available screen space
        initial_width = max(int(screen_geometry.width() * 0.6), 800) # 60% width, min 800
        initial_height = max(int(screen_geometry.height() * 0.7), 600) # 70% height, min 600
        print(f"Initial window size set to: {initial_width}x{initial_height}")

        # Center the window on the screen
        initial_x = screen_geometry.x() + (screen_geometry.width() - initial_width) // 2
        initial_y = screen_geometry.y() + (screen_geometry.height() - initial_height) // 2
        self.setGeometry(initial_x, initial_y, initial_width, initial_height)
        print(f"Initial window position set to: ({initial_x},{initial_y})")

        # Set minimum allowed size
        self.setMinimumSize(800, 600)

        # --- Central Widget and Main Layout ---
        # This widget holds the entire content (top bar + stacked pages)
        central_widget = QWidget(self)
        # Style the container - important for frameless window appearance
        central_widget.setStyleSheet("""
            QWidget {
                background-color: #121212; /* Main dark background */
                /* Add border for visual structure, adjust color/width as needed */
                /* border: 1px solid #444444; */ /* Optional border */
            }
        """)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0) # No margins, top bar and content fill edges
        main_layout.setSpacing(0) # No spacing between top bar and content area

        # --- Stacked Widget for Pages ---
        self.stacked_widget = QStackedWidget()
        initial_screen = InitialScreen(self.stacked_widget) # Pass stack as parent
        message_screen = MessageScreen(self.stacked_widget) # Pass stack as parent
        self.stacked_widget.addWidget(initial_screen) # Index 0
        self.stacked_widget.addWidget(message_screen) # Index 1

        # --- Custom Top Bar ---
        # Pass self (MainWindow) and the stacked_widget to the top bar
        self.top_bar = CustomTopBar(self, self.stacked_widget)

        # --- Assemble Main Layout ---
        main_layout.addWidget(self.top_bar) # Add top bar first
        main_layout.addWidget(self.stacked_widget, 1) # Add stacked widget, stretch factor 1

        # --- Window Icon ---
        try:
            app_icon_path = GraphicsDirectoryPath("app_icon.png")
            if os.path.exists(app_icon_path):
                self.setWindowIcon(QIcon(app_icon_path))
                print(f"Loaded application icon from: {app_icon_path}")
            else:
                print(f"Warning: Application icon not found at {app_icon_path}")
        except Exception as e:
             print(f"Error setting application icon: {e}")
             traceback.print_exc()

        print("MainWindow UI initialization complete.")


    def changeEvent(self, event):
        """Handle window state changes (minimize, maximize, restore)."""
        super().changeEvent(event) # Call base class implementation first
        if event.type() == QEvent.WindowStateChange:
            # Check if the top bar exists (it should, but good practice)
            if hasattr(self, 'top_bar') and self.top_bar:
                # The window state has changed (e.g., maximized, minimized, restored)
                # Use QTimer.singleShot to ensure the update happens after the event processing
                window_state = self.windowState()
                state_str = "Unknown"
                if window_state == Qt.WindowNoState: state_str = "Normal"
                elif window_state == Qt.WindowMinimized: state_str = "Minimized"
                elif window_state == Qt.WindowMaximized: state_str = "Maximized"
                elif window_state == Qt.WindowFullScreen: state_str = "FullScreen"
                elif window_state == Qt.WindowActive: state_str = "Active" # Might be combined

                print(f"Window state changed to: {state_str} ({window_state})")
                print("Scheduling updateMaximizeButtonIcon...")
                # Update the maximize/restore button icon asynchronously
                QTimer.singleShot(0, self.top_bar.updateMaximizeButtonIcon)
            else:
                print("Warning: Window state changed but top_bar not found.")


    def closeEvent(self, event):
        """Handle the window close event."""
        print("Close event triggered. Cleaning up...")
        # Add any cleanup tasks here if needed (e.g., stopping threads, saving state)
        # Set mic status to False on close?
        # SetMicrophoneStatus("False")
        # print("Set Mic Status to False on close.")
        super().closeEvent(event) # Accept the close event


# --- Main Execution Function ---

def GraphicalUserInterface():
    """Initializes and runs the PyQt application."""
    print("--- Starting GraphicalUserInterface ---")
    print("Initializing data files...")
    # Ensure essential files exist or are created with defaults
    try:
        GetMicrophoneStatus() # Reads/Creates Mic.data
        GetAssistantStatus()  # Reads/Creates Status.data
        _safe_file_read(TempDirectoryPath('Responses.data')) # Reads/Creates Responses.data
        print("Data files checked/initialized successfully.")
    except Exception as e:
        print(f"ERROR during data file initialization: {e}")
        traceback.print_exc()
        # Decide if the error is fatal
        # return # Optional: Exit if file setup fails critically

    # --- Application Setup ---
    # Enable High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    print("High DPI scaling and pixmaps enabled.")

    app = QApplication(sys.argv)

    # --- Global Stylesheet ---
    # Apply base styles to common widgets
    app.setStyleSheet("""
        /* Global fallback styles */
        QWidget {
            background-color: #121212; /* Base dark background */
            color: #f0f0f0; /* Default light text color */
            font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif; /* Font stack */
            font-size: 14px; /* Default font size */
        }
        QMainWindow#MainWindow {
            /* Specific styles for the main window container if needed */
            /* border: 2px solid #55aaff; */ /* Example: Blue border for debugging */
        }
        QLabel {
            background-color: transparent; /* Labels should generally be transparent */
            color: #cccccc; /* Slightly dimmer default text for labels */
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #f0f0f0;
            border: 1px solid #333333; /* Subtle border */
            border-radius: 5px;
            padding: 8px; /* Padding inside the text edit */
            font-size: 14px; /* Ensure font size consistency */
        }
        /* General QPushButton style (can be overridden) */
        QPushButton {
            background-color: #333333;
            color: #f0f0f0;
            border: 1px solid #555555; /* Default border */
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 14px;
            min-height: 28px; /* Minimum button height */
        }
        QPushButton:hover {
            background-color: #444444;
            border-color: #777777;
        }
        QPushButton:pressed {
            background-color: #505050;
        }
        QPushButton:disabled {
            background-color: #2a2a2a; /* Darker when disabled */
            color: #555555; /* Grayed out text */
            border-color: #444444;
        }
        QPushButton:focus {
             outline: none; /* Remove dotted focus border */
             /* Optional: Add a subtle focus indicator if desired */
             /* border: 1px solid #55aaff; */
        }
        /* Tooltip styling */
        QToolTip {
             background-color: #282828; /* Dark tooltip background */
             color: #f0f0f0; /* Light text */
             border: 1px solid #555; /* Tooltip border */
             padding: 5px; /* Padding inside tooltip */
             border-radius: 3px; /* Slightly rounded corners */
             opacity: 230; /* Semi-transparent (value 0-255) */
        }
        /* Scrollbar styling (applied globally, can be overridden like in ChatSection) */
        QScrollBar:vertical {
            border: none;
            background: #1e1e1e;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #555555;
            min-height: 30px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background: #666666;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none; height: 0px; border: none;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal { /* Basic horizontal scrollbar styling */
             border: none; background: #1e1e1e; height: 12px; margin: 0px;
        }
         QScrollBar::handle:horizontal {
             background: #555555; min-width: 30px; border-radius: 6px;
        }
        QScrollBar::handle:horizontal:hover { background: #666666; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { background: none; width: 0px; border: none; }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

    """)
    print("Global stylesheet applied.")

    print("Creating MainWindow instance...")
    window = MainWindow()
    print("Showing MainWindow...")
    window.show() # Make the window visible

    print("Starting application event loop (app.exec_())...")
    # Start the Qt event loop. Execution blocks here until the app closes.
    exit_code = app.exec_()
    print(f"Application event loop finished. Exiting with code: {exit_code}")
    sys.exit(exit_code)

# --- Entry Point ---
if __name__ == "__main__":
    try:
        GraphicalUserInterface()
    except SystemExit as e:
        print(f"Application exited normally with code: {e.code}")
    except Exception as e:
        # Catch any unexpected fatal errors during setup or runtime
        print(f"FATAL ERROR in GUI execution: {e}")
        traceback.print_exc()
        # Keep console open to see the error in non-interactive environments
        input("Press Enter to exit...")