import os
import sys
import cohere
import traceback
from rich import print
from dotenv import load_dotenv
from fuzzywuzzy import process
import Levenshtein  # For better string matching
import re  # For regex-based splitting

# --- Helper for PyInstaller path resolution ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# Load environment variables
load_dotenv(dotenv_path=resource_path('.env'))
CohereAPIKey = os.getenv("CohereAPIKey")

if not CohereAPIKey:
    print("[bold red]Error: Cohere API key not found. Please set it in the .env file.[/bold red]")
    raise ValueError("Cohere API key not found. Please set it in the .env file.")

co = cohere.Client(api_key=CohereAPIKey)

FUNC_CATEGORIES = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "reminder"
]

APPS_LIST = ["Facebook", "Telegram", "Instagram",
             "Chrome", "YouTube", "Spotify", "Notepad"]

def correct_app_name(app_name):
    match, score = process.extractOne(app_name, APPS_LIST)
    levenshtein_score = Levenshtein.ratio(app_name.lower(), match.lower())
    if score > 70 or levenshtein_score > 0.7:
        return match
    return app_name

# 🔧 Modified preamble
PREAMBLE = """ 
You are a highly accurate Decision-Making Model that categorizes user queries.
Your task is to classify queries into specific categories based on their nature.  

*** Do NOT answer queries-only categorize them. ***  

### **Classification Rules:**  

1️⃣ **General Queries**  
-> Respond with **'general ( query )'** if the query can be answered by an AI model (LLM) and does **not** require real-time or external data.  
   ✅ Examples:  
   - "What is the speed of light?" → **general ( What is the speed of light? )**  
   - "Who is Elon Musk?" → **general ( Who is Elon Musk? )**  
   - "Tell me about India" → **general ( Tell me about India )**  

2️⃣ **Google Search Queries**  
-> Respond with **'google search ( topic )'** ONLY if the query involves:  
   - Current or breaking news  
   - Latest product prices or updates  
   - Real-world events that are rapidly changing  
   ✅ Examples:  
   - "Latest news on Ukraine?" → **google search ( Latest news on Ukraine )**  
   - "Current iPhone 15 price" → **google search ( iPhone 15 price )**  

3️⃣ **Real-Time Queries**  
-> Respond with **'realtime ( query )'** if it involves **live** data like:  
   - Weather  
   - Live scores or traffic  
   ✅ Examples:  
   - "Is it raining in Delhi now?" → **realtime ( Is it raining in Delhi now )**  

4️⃣ **Application Commands**  
- **'open ( application name )'** → If a query asks to open an app or website.  
- **'close ( application name )'** → If a query asks to close an app.  

5️⃣ **Media Commands**  
- **'play ( song name )'** → If a query asks to play a song.  
- **'generate image ( prompt )'** → If a query asks to generate an image.  

6️⃣ **Utility & System Commands**  
- **'reminder ( datetime with message )'** → If a query is setting a reminder.  
- **'system ( task name )'** → For system actions like mute, volume, restart.  

7️⃣ **Content Requests**  
- **'content ( topic )'** → For generating content like code, emails, or essays.  

8️⃣ **YouTube Search Queries**  
- **'youtube search ( topic )'** → If a user wants to find a video on YouTube.  

9️⃣ **Exit Commands**  
- **'exit'** → If the user wants to end the conversation.  

---
⚠️ **STRICT INSTRUCTIONS** ⚠️  
🔹 Always return queries in the format: `category ( query )`.  
🔹 Never provide answers, only categorize them.  
🔹 If unsure, return: `general (uncategorized query)`
"""

def FirstLayerDMM(prompt: str, recursion_depth: int = 3):
    if recursion_depth == 0:
        return ["general (uncategorized query)"]

    try:
        if prompt.lower().startswith("open "):
            app_name = prompt[5:].strip()
            corrected_name = correct_app_name(app_name)
            return [f"open ( {corrected_name} )"]

        stream = co.chat_stream(
            model="command-r-plus",
            message=prompt,
            temperature=0.7,
            chat_history=[],
            prompt_truncation="OFF",
            connectors=[],
            preamble=PREAMBLE
        )

        response = []
        for event in stream:
            if event.event_type == "text-generation":
                response.append(event.text.strip())

        response_text = " ".join(response).replace("\n", " ").strip()

        response_tasks = [task.strip() for task in re.split(
            r",\s*|\s{2,}", response_text) if task.strip()]

        response_tasks = [task for task in response_tasks if any(
            task.startswith(func) for func in FUNC_CATEGORIES)]

        formatted_tasks = []
        for task in response_tasks:
            clean_task = " ".join(task.split())
            clean_task = clean_task.replace("un categor ized", "uncategorized")
            formatted_tasks.append(clean_task)

        return formatted_tasks if formatted_tasks else ["general (uncategorized query)"]

    except Exception as e:
        print(f"[bold red]Error:[/bold red] {e}")
        print(traceback.format_exc())
        return ["general (error processing query)"]

# Optional: Act on the classification
def handle_classified_output(response):
    for task in response:
        if task.startswith("google search"):
            if any(kw in task.lower() for kw in ["latest", "price", "current", "news", "today"]):
                print(f"[blue]🔎 Performing Google search:[/blue] {task}")
                # open_browser(task)  # Add your browser logic here
            else:
                print(f"[green]💬 Answer with AI:[/green] {task}")
                # answer_with_model(task)  # Add your AI logic here
        else:
            print(f"[yellow]🧠 Action:[/yellow] {task}")

# User loop
if __name__ == "__main__":
    while True:
        user_input = input(">>> ").strip()
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("[bold green]Goodbye![/bold green] 👋")
            break

        result = FirstLayerDMM(user_input)
        handle_classified_output(result)
