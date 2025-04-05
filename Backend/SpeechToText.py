import os
import re
import time
import logging
import threading
import atexit
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from dotenv import dotenv_values

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait

import mtranslate as mt

# ─── CONFIG & LOGGING ───────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
env = dotenv_values(".env")

INPUT_LANGUAGE   = env.get("InputLanguage", "en-US")
SPEECH_TIMEOUT   = int(env.get("SPEECH_TIMEOUT", 15))
EDGE_DRIVER_PATH = env.get("EDGE_DRIVER_PATH", "")
HEADLESS         = env.get("HEADLESS", "true").lower() in ("1","true","yes")
FAKE_AUDIO_PATH  = env.get("FAKE_AUDIO_PATH", "")

if not EDGE_DRIVER_PATH or not Path(EDGE_DRIVER_PATH).exists():
    raise RuntimeError(f"Invalid EDGE_DRIVER_PATH: {EDGE_DRIVER_PATH!r}")

# ─── GENERATE & SERVE HTML ─────────────────────────────────────────────────────
DATA_DIR = Path("Data")
DATA_DIR.mkdir(exist_ok=True)
HTML_PATH = DATA_DIR / "Voice.html"

# Adjust the JavaScript if you want to disable auto-restart after stop.
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Speech Recognition</title></head>
<body>
  <button id="start" onclick="startRecognition()">Start Recognition</button>
  <button id="end"   onclick="stopRecognition()">Stop Recognition</button>
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
      recognition.onend = () => {{
        if (autoRestart) recognition.start();
      }};
      recognition.start();
    }}
    function stopRecognition() {{
      autoRestart = false;
      if (recognition) recognition.stop();
      output.textContent = "";
    }}
  </script>
</body>
</html>"""

HTML_PATH.write_text(HTML, encoding="utf-8")
logging.info(f"Wrote HTML → {HTML_PATH}")

def _serve():
    os.chdir(DATA_DIR)
    HTTPServer(("localhost", 8000), SimpleHTTPRequestHandler).serve_forever()

threading.Thread(target=_serve, daemon=True).start()
logging.info("Serving Data/ on http://localhost:8000/")

# ─── SELENIUM SETUP ─────────────────────────────────────────────────────────────
opts = Options()
opts.add_argument("--use-fake-ui-for-media-stream")
opts.add_argument("--use-fake-device-for-media-stream")
opts.add_argument("--allow-file-access-from-files")
if FAKE_AUDIO_PATH:
    opts.add_argument(f"--use-file-for-fake-audio-capture={FAKE_AUDIO_PATH}")
if HEADLESS:
    opts.add_argument("--headless=new")
opts.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59"
)

service = Service(executable_path=EDGE_DRIVER_PATH)
driver  = webdriver.Edge(service=service, options=opts)
atexit.register(lambda: driver.quit())
logging.info("Edge launched successfully")

PAGE_URL = "http://localhost:8000/Voice.html"

# ─── HELPERS ────────────────────────────────────────────────────────────────────
def QueryModifier(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text[-1] not in ".?!":
        if re.match(r"^(how|what|who|where|when|why|which)\b", text, re.I):
            text += "?"
        else:
            text += "."
    return text[0].upper() + text[1:]

def UniversalTranslator(text: str) -> str:
    eng = mt.translate(text, "en", "auto")
    return eng.strip().capitalize()

# ─── SPEECH LOOP ────────────────────────────────────────────────────────────────
def SpeechRecognition() -> str | None:
    driver.get(PAGE_URL)
    WebDriverWait(driver, 5).until(lambda d: d.find_element(By.ID, "start").is_displayed())
    logging.info("Clicking Start Recognition")
    driver.find_element(By.ID, "start").click()

    # give you a moment to speak
    time.sleep(1.0)

    try:
        logging.info("Waiting for speech result…")
        # wait until #output.text is non‑empty
        WebDriverWait(driver, SPEECH_TIMEOUT).until(
            lambda d: d.find_element(By.ID, "output").text.strip() != ""
        )
        # re-fetch the element to get its .text
        raw = driver.find_element(By.ID, "output").text.strip()
        logging.info(f"Raw recognition: {raw!r}")
    except Exception as e:
        logging.warning(f"No speech detected (or timeout): {e}")
        # try to stop gracefully
        try: 
            driver.find_element(By.ID, "end").click()
        except Exception:
            pass
        return None

    # stop recognition
    try:
        driver.find_element(By.ID, "end").click()
    except Exception:
        pass

    if INPUT_LANGUAGE.lower().startswith("en"):
        return QueryModifier(raw)
    else:
        return QueryModifier(UniversalTranslator(raw))

# ─── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.info("Entering main loop. Say 'stop' to exit.")
    try:
        while True:
            result = SpeechRecognition()
            if result:
                print("→", result)
                # Check for stop command. Adjust the phrase as needed.
                if result.strip().lower().startswith("stop"):
                    logging.info("Stop command detected. Exiting loop.")
                    break
            else:
                logging.info("No input—retrying in 1s.")
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutdown requested, exiting…")
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
