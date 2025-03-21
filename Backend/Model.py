import os
import cohere
from rich import print
from dotenv import dotenv_values
from fuzzywuzzy import process

# Load environment variables
env_vars = dotenv_values(".env")
CohereAPIKey = env_vars.get("CohereAPIKey")

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

# Commonly used applications
APPS_LIST = ["Facebook", "Telegram", "Instagram",
             "Chrome", "YouTube", "Spotify", "Notepad"]

# Function to correct app names using fuzzy matching


def correct_app_name(app_name):
    match, score = process.extractOne(app_name, APPS_LIST)
    return match if score > 70 else app_name  # Correct only if confidence > 70


# Preamble defining classification rules for Cohere model
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
"""

# Decision-making function


def FirstLayerDMM(prompt: str, recursion_depth: int = 3):
    if recursion_depth == 0:
        return ["general (uncategorized query)"]  # Prevent infinite recursion

    try:
        # Handle "open" command manually before calling Cohere
        if prompt.lower().startswith("open "):
            app_name = prompt[5:].strip()  # Extract app name
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
            preamble=PREAMBLE  # Adding preamble back
        )

        # Collect response text from the stream
        response = ""
        for event in stream:
            if event.event_type == "text-generation":
                response += event.text

        # Process response
        response = [task.strip() for task in response.replace(
            "\n", " ").split(",") if task.strip()]

        # Filter recognized function categories
        response = [task for task in response if any(
            task.startswith(func) for func in FUNC_CATEGORIES)]

        # Handle unknown queries gracefully
        return response if response else ["general (uncategorized query)"]

    except Exception as e:
        print(f"[bold red]Error:[/bold red] {e}")
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
