import os
import cohere
import traceback
from rich import print
from dotenv import dotenv_values
from fuzzywuzzy import process
import Levenshtein  # For better string matching
import re  # For regex-based splitting

# Load environment variables
env_vars = dotenv_values(".env")
CohereAPIKey = env_vars.get("CohereAPIKey") or os.getenv(
    "CohereAPIKey")  # Fallback if needed

# Handle missing API key
if not CohereAPIKey:
    print("[bold red]Error: Cohere API key not found. Please set it in the .env file.[/bold red]")
    raise ValueError(
        "Cohere API key not found. Please set it in the .env file.")

# Initialize Cohere client
co = cohere.Client(api_key=CohereAPIKey)

# Recognized function keywords
FUNC_CATEGORIES = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "reminder"
]

# Commonly used applications for fuzzy matching
APPS_LIST = ["Facebook", "Telegram", "Instagram",
             "Chrome", "YouTube", "Spotify", "Notepad"]

# Improved function to correct app names using fuzzy matching + Levenshtein check


def correct_app_name(app_name):
    match, score = process.extractOne(app_name, APPS_LIST)
    levenshtein_score = Levenshtein.ratio(app_name.lower(), match.lower())
    if score > 70 or levenshtein_score > 0.7:
        return match
    return app_name


# Define the preamble for classification
PREAMBLE = """ 
You are a highly accurate Decision-Making Model that categorizes user queries.
Your task is to classify queries into specific categories based on their nature.  

*** Do NOT answer queries—only categorize them. ***  

### **Classification Rules:**  

1️⃣ **General Queries**  
-> Respond with **'general ( query )'** if the query can be answered by an AI model (LLM) and does **not** require real-time or external data.  
   ✅ Examples:  
   - "What is the speed of light?" → **general ( What is the speed of light? )**  
   - "What is the capital of France?" → **general ( What is the capital of France? )**  
   🚨 **EXCEPTION:** If the query is about a public figure or a time-sensitive event, classify it as a **Google search** instead.  

2️⃣ **Google Search Queries**  
-> Respond with **'google search ( topic )'** if the query is about:  
   - Public figures (celebrities, politicians, athletes, etc.)  
   - Places, recent events, or historical events  
   - Any data that changes over time (e.g., "latest iPhone price")  
   ✅ Examples:  
   - "Who is Virat Kohli?" → **google search ( Who is Virat Kohli? )**  
   - "Latest news on Ukraine?" → **google search ( Latest news on Ukraine? )**  

3️⃣ **Real-Time Queries**  
-> Respond with **'realtime ( query )'** if the query requires **live** or **dynamic** data that changes frequently.  
   ✅ Examples:  
   - "What is the current price of Bitcoin?" → **realtime ( current price of Bitcoin )**  
   - "Is it raining in Mumbai right now?" → **realtime ( Is it raining in Mumbai right now? )**  

4️⃣ **Application Commands**  
- **'open ( application name )'** → If a query asks to open an app or website.  
  ✅ Example: "Open Facebook" → **open ( Facebook )**  
- **'close ( application name )'** → If a query asks to close an app.  
  ✅ Example: "Close Notepad" → **close ( Notepad )**  

5️⃣ **Media Commands**  
- **'play ( song name )'** → If a query asks to play a song.  
  ✅ Example: "Play Let Her Go" → **play ( Let Her Go )**  
- **'generate image ( prompt )'** → If a query asks to generate an image.  

6️⃣ **Utility & System Commands**  
- **'reminder ( datetime with message )'** → If a query is setting a reminder.  
- **'system ( task name )'** → If a query involves system actions like mute, volume control, etc.  

7️⃣ **Content Requests**  
- **'content ( topic )'** → If a query asks to generate content (e.g., code, emails, articles).  

8️⃣ **YouTube Search Queries**  
- **'youtube search ( topic )'** → If a query is about finding a video on YouTube.  

9️⃣ **Exit Commands**  
- **'exit'** → If the user wants to end the conversation.  

---
⚠️ **STRICT INSTRUCTIONS** ⚠️  
🔹 Always return queries in the structured format: `category ( query )`.  
🔹 Never provide direct answers, only categorize them.  
🔹 If unsure, categorize under "general (uncategorized query)".
"""

# Decision-making function


def FirstLayerDMM(prompt: str, recursion_depth: int = 3):
    if recursion_depth == 0:
        return ["general (uncategorized query)"]

    try:
        # Handle "open" command manually
        if prompt.lower().startswith("open "):
            app_name = prompt[5:].strip()
            corrected_name = correct_app_name(app_name)
            return [f"open ( {corrected_name} )"]

        # Call Cohere API for classification
        stream = co.chat_stream(
            model="command-r-plus",
            message=prompt,
            temperature=0.7,
            chat_history=[],
            prompt_truncation="OFF",
            connectors=[],
            preamble=PREAMBLE
        )

        # Collect response text from the stream
        response = []
        for event in stream:
            if event.event_type == "text-generation":
                response.append(event.text.strip())

        # Process the response safely
        response_text = " ".join(response).replace("\n", " ").strip()
        #print(f"[DEBUG] Raw response: {response_text}")  #Debugging line

        # Use regex to split on commas or multiple spaces
        response_tasks = [task.strip() for task in re.split(
            r",\s*|\s{2,}", response_text) if task.strip()]

        # Filter recognized function categories
        response_tasks = [task for task in response_tasks if any(
            task.startswith(func) for func in FUNC_CATEGORIES)]

        # Final formatting: remove extra spaces and fix known issues
        formatted_tasks = []
        for task in response_tasks:
            clean_task = " ".join(task.split())
            # If the misformatted text "un categor ized" exists, replace it
            clean_task = clean_task.replace("un categor ized", "uncategorized")
            formatted_tasks.append(clean_task)

        return formatted_tasks if formatted_tasks else ["general (uncategorized query)"]

    except Exception as e:
        print(f"[bold red]Error:[/bold red] {e}")
        print(traceback.format_exc())
        return ["general (error processing query)"]


# Entry point: User input loop
if __name__ == "__main__":
    while True:
        user_input = input(">>> ").strip().lower()
        if user_input in ["exit", "quit", "bye"]:
            print("[bold green]Goodbye![/bold green] 👋")
            break

        response = FirstLayerDMM(user_input)
        print(response)
