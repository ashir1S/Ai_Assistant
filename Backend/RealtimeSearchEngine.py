# RealtimeSearchEngine.py
import os
import sys
from serpapi import GoogleSearch
from groq import Groq
from json import load, dump
import datetime
from dotenv import load_dotenv

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# Load environment variables correctly
load_dotenv(dotenv_path=resource_path('.env'))

# Get environment variables using os.getenv()
Username = os.getenv("Username", "User") # Added default value
Assistantname = os.getenv("Assistantname", "Assistant") # Added default value
GroqAPIKey = os.getenv("GroqAPIKey")
SerpAPIKey = os.getenv("SerpAPIKey")

# Initialize Groq client with proper error handling
if not GroqAPIKey:
    raise ValueError("Groq API key not found in environment variables")

client = Groq(api_key=GroqAPIKey)

# --- Step 1: Strengthen the System Prompt ---
System = f"""Hello, I am {Username}. You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Always answer ONLY using the provided search results below. If the answer is not found in the results, respond: 'I could not find the answer in the latest search results.' ***
*** Provide answers in a professional way, with proper grammar and punctuation. ***
"""

# Chat log handling with proper path resolution
chatlog_path = resource_path(os.path.join("Data", "ChatLog.json"))
data_dir = os.path.dirname(chatlog_path)
os.makedirs(data_dir, exist_ok=True)

# Load chat log, initialize if not found
try:
    with open(chatlog_path, "r") as f:
        messages_log = load(f) # Renamed to avoid conflict with messages variable in completion call
except FileNotFoundError:
    with open(chatlog_path, "w") as f:
        dump([], f)
    messages_log = []

def truncate_text(text, max_length=1000):
    """Truncate text to specified max length"""
    return text[:max_length] + "..." if len(text) > max_length else text

def PerformGoogleSearch(query):
    if not SerpAPIKey:
        # Return an indicator of the missing key instead of raising an error immediately
        # Allows the main function to handle it gracefully if needed
        return "Error: SerpAPI key not found."

    try:
        search = GoogleSearch({
            "q": query,
            "api_key": SerpAPIKey,
            "num": 5 # Limit to 5 results
        })
        results = search.get_dict().get("organic_results", [])

        if not results:
             # Indicate no results found
            return "No results found."

        answer = f"The search results for '{query}' are:\n[start]\n"
        found_content = False
        for result in results:
            title = result.get("title", "No Title")
            snippet = result.get("snippet", "No Description")
            # Only include if there's a title or a meaningful snippet
            if title != "No Title" or snippet != "No Description":
                answer += f"Title: {title}\nDescription: {truncate_text(snippet, 150)}\n\n"
                found_content = True

        if not found_content:
             # Indicate results were present but lacked usable titles/snippets
             return "No relevant information found in search results."

        answer += "[end]"
        return truncate_text(answer, 1000) # Truncate the final result string if needed

    except Exception as e:
        # Catch potential API errors or other issues
        print(f"Error during Google Search: {e}")
        return f"Error performing search: {e}"


def AnswerModifier(answer):
    # Simple modifier, removes extra newlines
    return '\n'.join([line for line in answer.split('\n') if line.strip()])

# Removed SystemChatBot as per Step 3

# Removed Information() function as it's not used in the new conversation structure (Step 3)

def RealtimeSearchEngine(prompt):
    global messages_log # Use the renamed chat log variable

    # Load the latest chat log (optional, depends if you want context from previous turns)
    # For strict adherence to Step 3 (fresh list each time), we don't load previous messages here.
    # However, we still load it to *append* the current exchange for logging purposes later.
    try:
        with open(chatlog_path, "r") as f:
            messages_log = load(f)
    except FileNotFoundError:
        messages_log = [] # Start fresh if log file is missing

    # Perform search *before* building the conversation
    search_data = PerformGoogleSearch(prompt)

    # --- Step 5: Handle No Search Results Gracefully ---
    # Check for error messages or lack of relevant content from PerformGoogleSearch
    if "Error:" in search_data or "No results found." in search_data or "No relevant information found" in search_data:
         # Log the user prompt and the error/no result message
        messages_log.append({"role": "user", "content": prompt})
        no_result_message = "I could not find relevant information in the latest search results."
        if "Error: SerpAPI key not found." in search_data:
             no_result_message = "Search is unavailable due to a missing API key configuration."
        elif "Error performing search:" in search_data:
             no_result_message = "An error occurred while trying to fetch search results."

        messages_log.append({"role": "assistant", "content": no_result_message})
        with open(chatlog_path, "w") as f:
            dump(messages_log, f, indent=4)
        return no_result_message

    # --- Step 2: Change How You Add Search Results ---
    search_message = {
        "role": "user",
        "content": f"Here are the latest search results for your query:\n{search_data}\n\nUsing ONLY this information, answer the following question: {prompt}"
    }

    # --- Step 3: Build a Fresh Message List for Each Query ---
    conversation = [
        {"role": "system", "content": System},
        search_message
        # Note: No history (`messages_log` or `recent_messages`) is included here as per Step 3
        # Note: Information() call is removed as per Step 3's structure
    ]

    try:
        # --- Step 4: Update the Completion Call ---
        completion = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=conversation, # Use the new conversation list
            temperature=0.7,
            max_tokens=2048,
            top_p=1,
            stream=True,
        )

        answer = ""
        for chunk in completion:
             # Check if delta content exists before accessing it
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content

        answer = answer.strip().replace("</s>", "") # Clean up potential end tokens

        # Check if the model couldn't find the answer in the provided results
        if not answer or "could not find the answer in the latest search results" in answer.lower():
             answer = "I could not find the answer in the latest search results."

    except Exception as e:
        print(f"Error during Groq API call: {e}")
        answer = "Sorry, I encountered an error while processing your request."

    # Log the actual user prompt and the final answer
    messages_log.append({"role": "user", "content": prompt})
    messages_log.append({"role": "assistant", "content": answer})
    with open(chatlog_path, "w") as f:
        dump(messages_log, f, indent=4)

    return AnswerModifier(answer)

if __name__ == "__main__":
    print(f"Starting {Assistantname}. Type 'exit', 'quit', or 'bye' to end.")
    while True:
        prompt = input(f"{Username}: ")
        if prompt.lower() in ['exit', 'quit', 'bye']:
            print(f"{Assistantname}: Goodbye!")
            break
        response = RealtimeSearchEngine(prompt)
        print(f"{Assistantname}: {response}")