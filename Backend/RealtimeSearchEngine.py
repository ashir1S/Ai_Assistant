# RealtimeSearchEngine.py
from serpapi import GoogleSearch  # Imported SerpAPI's GoogleSearch class
from groq import Groq  # Importing the Groq library to use its API.
from json import load, dump  # Functions to read and write JSON files.
import datetime  # For real-time date and time information.
from dotenv import dotenv_values  # To read environment variables from a .env file

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

# Initialize the Groq client with the provided API key.
client = Groq(api_key=GroqAPIKey)

# Define the system instructions for the chatbot.
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Just answer the question from the provided data in a professional way. ***"""

# Try to load the chat log from a JSON file; if not available, create an empty one.
try:
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
except Exception as e:
    with open(r"Data\ChatLog.json", "w") as f:
        dump([], f)
    messages = []

def truncate_text(text, max_length=1000):
    """Truncate text to the maximum length specified."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

# Function to perform a Google search and format the results using SerpAPI.
def PerformGoogleSearch(query):
    search = GoogleSearch({
        "q": query,
        "api_key": env_vars.get("SerpAPIKey"),
        "num": 5
    })
    response = search.get_dict()  # Get the full response as a dictionary.
    results = response.get("organic_results", [])

    Answer = f"The search results for '{query}' are:\n[start]\n"
    for result in results:
        title = result.get("title", "No Title")
        snippet = result.get("snippet", "No Description")
        # Optionally truncate each snippet if too long.
        snippet = truncate_text(snippet, 150)
        Answer += f"Title: {title}\nDescription: {snippet}\n\n"
    Answer += "[end]"
    # Also truncate the overall answer if needed.
    return truncate_text(Answer, 1000)

# Function to clean up the answer by removing empty lines.
def AnswerModifier(answer):
    lines = answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

# Predefined chatbot conversation system message and an initial conversation.
SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"}
]

# Function to get real-time information like the current date and time.
def Information():
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")
    data = (
        f"Use This Real-time Information if needed:\n"
        f"Day: {day}\n"
        f"Date: {date}\n"
        f"Month: {month}\n"
        f"Year: {year}\n"
        f"Time: {hour} hours, {minute} minutes, {second} seconds.\n"
    )
    return data

# Function to handle real-time search and response generation.
def RealtimeSearchEngine(prompt):
    global SystemChatBot, messages

    # Load the chat log from the JSON file.
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)

    # Append the user prompt to the messages.
    messages.append({"role": "user", "content": prompt})
    
    # Limit the context to the last 5 messages.
    recent_messages = messages[-5:]

    # Add Google search results (from SerpAPI) to the system chatbot messages.
    SystemChatBot.append({"role": "system", "content": PerformGoogleSearch(prompt)})

    # Compose the full conversation with trimmed context.
    full_conversation = SystemChatBot + [{"role": "system", "content": Information()}] + recent_messages

    # Generate a response using the Groq client.
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=full_conversation,
        temperature=0.7,
        max_tokens=2048,
        top_p=1,
        stream=True,
    )

    Answer = ""
    # Concatenate response chunks from the streaming output.
    for chunk in completion:
        if chunk.choices[0].delta.content:
            Answer += chunk.choices[0].delta.content

    # Clean up the response.
    Answer = Answer.strip().replace("</s>", "")
    messages.append({"role": "assistant", "content": Answer})

    # Save the updated chat log back to the JSON file.
    with open(r"Data\ChatLog.json", "w") as f:
        dump(messages, f, indent=4)

    # Remove the most recent system message (the search result) from the conversation.
    SystemChatBot.pop()

    return AnswerModifier(Answer)

# Main entry point of the program for interactive querying.
if __name__ == "__main__":
    while True:
        prompt = input("Enter your query: ")
        if prompt.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        print(RealtimeSearchEngine(prompt))
