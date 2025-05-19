import os
import re
import sys
import time
import logging
import threading
import atexit
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import mtranslate as mt
import tempfile

# ─── PATH HELPER ──────────────────────────────────────────────────────────────
def resource_path(relative_path):
    """Get absolute path for PyInstaller and dev mode"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# ─── CONFIG & LOGGING ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Load environment variables from correct location
load_dotenv(dotenv_path=resource_path('.env'))

INPUT_LANGUAGE   = os.getenv("InputLanguage", "en-US")
SPEECH_TIMEOUT   = int(os.getenv("SPEECH_TIMEOUT", "15"))
EDGE_DRIVER_PATH = resource_path(os.getenv("EDGE_DRIVER_PATH", "Webdriver/msedgedriver.exe"))
HEADLESS         = os.getenv("HEADLESS", "true").lower() in ("1","true","yes")
FAKE_AUDIO_PATH  = resource_path(os.getenv("FAKE_AUDIO_PATH", ""))

# Validate critical paths
if not Path(EDGE_DRIVER_PATH).exists():
    raise FileNotFoundError(f"EdgeDriver not found at: {EDGE_DRIVER_PATH}")

# ─── HTML SERVER SETUP ────────────────────────────────────────────────────────
DATA_DIR = Path(resource_path("Data"))
HTML_PATH = DATA_DIR / "Voice.html"

HTML_CONTENT = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Speech Recognition</title></head>
<body>
  <button id="start" onclick="startRecognition()">Start</button>
  <button id="end" onclick="stopRecognition()">Stop</button>
  <p id="output"></p>
  <script>
    const output = document.getElementById('output');
    let recognition;
    let autoRestart = true;
    function startRecognition() {{
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SR();
      recognition.lang = '{INPUT_LANGUAGE}';
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.onresult = e => {{
        output.textContent = e.results[e.results.length-1][0].transcript;
      }};
      recognition.onend = () => autoRestart && recognition.start();
      recognition.start();
    }}
    function stopRecognition() {{
      autoRestart = false;
      recognition?.stop();
      output.textContent = "";
    }}
  </script>
</body>
</html>"""

DATA_DIR.mkdir(exist_ok=True)
HTML_PATH.write_text(HTML_CONTENT, encoding="utf-8")
logging.info(f"Created speech HTML at: {HTML_PATH}")

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silence HTTP server logs

def run_server():
    """Run HTTP server in background with diagnostics"""
    serve_dir = str(DATA_DIR)
    print("Serving from:", serve_dir)
    print("Voice.html exists:", os.path.exists(os.path.join(serve_dir, "Voice.html")))
    os.chdir(serve_dir)
    server = HTTPServer(("localhost", 8000), CustomHTTPRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    logging.info("Speech server started at http://localhost:8000/Voice.html")

run_server()

# ─── BROWSER CONFIGURATION ────────────────────────────────────────────────────
def configure_browser():
    opts = Options()
    opts.add_argument("--use-fake-ui-for-media-stream")
    opts.add_argument("--use-fake-device-for-media-stream")
    opts.add_argument("--allow-file-access-from-files")
    user_data_dir = tempfile.mkdtemp()
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    if FAKE_AUDIO_PATH:
        opts.add_argument(f"--use-file-for-fake-audio-capture={FAKE_AUDIO_PATH}")
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    )
    return opts

MAX_RETRIES = 3
driver = None
for attempt in range(MAX_RETRIES):
    try:
        service = Service(executable_path=EDGE_DRIVER_PATH)
        driver = webdriver.Edge(service=service, options=configure_browser())
        atexit.register(driver.quit)
        logging.info("Edge browser started successfully")
        break
    except Exception as e:
        logging.warning(f"Browser start attempt {attempt+1} failed: {e}")
        time.sleep(2)
if not driver:
    logging.error("Failed to start Edge browser after multiple attempts")
    sys.exit(1)

# ─── SPEECH RECOGNITION ────────────────────────────────────────────────────────
def QueryModifier(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text[-1] not in ".?!":
        text += "?" if re.match(r"^(how|what|who|where|when|why|which)\b", text, re.I) else "."
    return text[0].upper() + text[1:]

def UniversalTranslator(text: str) -> str:
    try:
        return mt.translate(text, "en", "auto").strip().capitalize()
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return text

def SpeechRecognition() -> str | None:
    try:
        driver.get("http://localhost:8000/Voice.html")
        WebDriverWait(driver, 10).until(
            lambda d: d.find_element(By.ID, "start").is_displayed()
        )
        driver.find_element(By.ID, "start").click()
        time.sleep(1)
        WebDriverWait(driver, SPEECH_TIMEOUT).until(
            lambda d: d.find_element(By.ID, "output").text.strip() != ""
        )
        raw_text = driver.find_element(By.ID, "output").text.strip()
        logging.info(f"Raw input: {raw_text}")
        return (
            QueryModifier(raw_text)
            if INPUT_LANGUAGE.lower().startswith("en")
            else QueryModifier(UniversalTranslator(raw_text))
        )
    except Exception as e:
        logging.warning(f"Recognition failed: {e}")
        return None
    finally:
        try:
            driver.find_element(By.ID, "end").click()
        except:
            pass

# ─── MAIN EXECUTION ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("Speech recognition system ready")
    try:
        while True:
            result = SpeechRecognition()
            if result:
                print(f"Recognized: {result}")
                if "stop" in result.lower():
                    logging.info("Stop command received")
                    break
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down gracefully")
    except Exception as e:
        logging.critical(f"Critical failure: {e}")
    finally:
        if driver:
            driver.quit()
        sys.exit(0)
