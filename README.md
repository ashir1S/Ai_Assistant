# 🤖 AI Assistant

AI Assistant is a versatile virtual assistant designed with both command-line (CLI) and graphical user interfaces (GUI). It aims to provide intelligent assistance across various tasks, leveraging multiple powerful AI APIs. This assistant can handle general queries, fetch real-time information, generate images, process voice commands, and automate basic desktop operations.

🔗 **GitHub Repository:** [https://github.com/ashir1S/Ai_Assistant](https://github.com/ashir1S/Ai_Assistant)

## 🚀 Features

* **💬 General Knowledge:** Ask complex questions, get explanations, and more, powered by large language models (LLMs).
* **🌍 Real-Time Information:** Fetches up-to-date data on current events, personalities, weather, etc., using search APIs like SerpAPI.
* **🖼️ AI Image Generation:** Creates images from your text descriptions via APIs like Hugging Face.
* **🗣️ Voice Support:** Enables hands-free interaction through integrated Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities.
* **⚙️ Task Automation:** Automates local tasks like opening applications (`"Open Chrome"`), searching specific websites, or running system commands via Selenium and OS modules.
* **🖥️ Graphical User Interface (GUI):** Offers a user-friendly visual interface built with PyQt5, featuring animations and clear display of interactions.
* **🔑 Multi-API Support:** Seamlessly integrates with APIs from OpenAI, Cohere, Groq, Hugging Face, and SerpAPI for robust and diverse functionalities.

## 📦 Installation

### Prerequisites

* Python 3.x installed.
* `pip` (Python package installer).
* `git` for cloning the repository.
* A working microphone (for voice input) and speakers/headphones (for voice output).
* Microsoft Edge browser installed (for default web automation).

### Setup Steps

1.  **Clone the Repository:**
    Open your terminal or command prompt and navigate to where you want to store the project.
    ```bash
    git clone [https://github.com/ashir1S/Ai_Assistant.git](https://github.com/ashir1S/Ai_Assistant.git)
    cd Ai_Assistant
    ```

2.  **Create a Virtual Environment (Recommended):**
    Using a virtual environment keeps project dependencies isolated.
    ```bash
    # Create the environment (e.g., named 'venv')
    python -m venv venv
    # Activate it
    # Windows:
    # venv\Scripts\activate
    # macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Install all required libraries using the provided `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```
    *(Alternatively, for manual installation or troubleshooting, you might install key packages like: `pip install openai PyQt5 python-dotenv requests pygame opencv-python SpeechRecognition pyttsx3 cohere groqsdk serpapi huggingface_hub Pillow selenium webdriver-manager`)*

4.  **Configure Environment Variables (`.env`):**
    Create a file named `.env` in the root directory (`Ai_Assistant`). This file stores your secret keys and configurations. **Do not commit this file to Git.** Populate it like this:

    ```dotenv
    # --- API Keys (REQUIRED - Get from respective service dashboards) ---
    CohereAPIKey=your_cohere_api_key         # From cohere.com
    GroqAPIKey=your_groq_api_key             # From groq.com
    SerpAPIKey=your_serpapi_key             # From serpapi.com
    HuggingFaceAPIKey=your_huggingface_api_key # From huggingface.co
    # OpenAI API Key (Optional: uncomment and add if using OpenAI features)
    # OPENAI_API_KEY=your_openai_api_key      # From openai.com

    # --- User & Assistant Configuration ---
    Username=YourName                       # Your preferred name
    Assistantname=Nova                      # Name for the AI assistant
    InputLanguage=en-US                     # Language code for STT (e.g., en-GB, es-ES)
    SPEECH_TIMEOUT=15                       # Seconds to wait for voice input

    # --- Webdriver Configuration (For Automation.py) ---
    # Path to your Microsoft Edge WebDriver executable.
    # Download matching your Edge version: [https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/)
    # IMPORTANT: Update this path!
    EDGE_DRIVER_PATH=C:/path/to/your/msedgedriver.exe

    # Option: Consider using webdriver-manager (if installed & code supports it) to handle driver download/updates automatically.

    # Headless Mode for Browser Automation
    HEADLESS=false                          # true = hide browser window; false = show browser window
    ```
    * **API Keys:** Obtain these by signing up on the respective platforms.
    * **WebDriver:** Essential for browser automation tasks. Ensure the path is correct and the driver version matches your installed Edge browser.

## 🎮 Usage

You can interact with the AI Assistant in two ways:

### 💻 Command-Line Mode

Run the assistant directly in your terminal. Good for quick queries and testing.
```bash
python main.py
```

## 🖼️ GUI Mode

Launch the graphical interface for a richer, more visual interaction experience.

```bash
python Gui.py
```

## 🔎 Sample Queries
Try interacting with the assistant using queries like these:

* "Explain black holes in simple terms" (General Knowledge)
* "Who won the last Formula 1 race?" (Real-time Info)
* "Open Spotify" (Task Automation)
* "Generate an image of a futuristic city skyline at sunset" (Image Generation)
* "What is my current location?" (Real-time / Contextual - may require specific implementation)
* (Spoken) "Set a timer for 5 minutes" (Voice Command + Task Automation - may require specific implementation)
* "Tell me a joke" (General Knowledge / Conversational)

## ❓ Quick Troubleshooting
* **API Errors:** Check `.env` for correct keys, names, and file location. Verify key status on provider's website.
* **Voice Input:** Check mic connection & system settings. Verify `InputLanguage` in `.env`. Ensure related libraries (`SpeechRecognition`, `PyAudio`) installed.
* **GUI Issues:** Ensure `PyQt5` installed. Check asset paths (if any). Look for console errors. Check `WebDriver` setup in `.env` if browser-related errors occur.
* **Automation Failures:** Verify `EDGE_DRIVER_PATH` & `WebDriver` version match Edge browser in `.env`. Check `HEADLESS` setting. Ensure Edge browser is installed.

## 📚 References & Technologies
* **Core:** Python 3
* **GUI:** PyQt5
* **AI Models:** OpenAI API, Cohere API, Groq API
* **Search:** SerpAPI
* **Image Gen:** Hugging Face Hub (`huggingface_hub`)
* **Voice:** SpeechRecognition, pyttsx3, Pygame (for audio playback)
* **Automation:** Selenium, os, subprocess modules
* **Configuration:** python-dotenv