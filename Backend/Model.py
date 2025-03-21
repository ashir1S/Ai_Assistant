import cohere  # Import the Cohere library for AI services.
from rich import print  # Import the Rich library to enhance terminal outputs.
# Import dotenv to load environment variables from a .env file.
from dotenv import dotenv_values

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")

# Retrieve API key.
CohereAPIKey = env_vars.get("CohereAPIKey")

# Handle missing API key.
if not CohereAPIKey:
    print("[bold red]Error: Cohere API key not found. Please set it in the .env file.[/bold red]")
    raise ValueError(
        "Cohere API key not found. Please set it in the .env file.")

# Create a Cohere client using the provided API key.
co = cohere.Client(api_key=CohereAPIKey)

# Define a list of recognized function keywords for task categorization.
funcs = [
    "exit", "general", "realtime", "open", "close", "play",
    "generate image", "system", "content", "google search",
    "youtube search", "reminder"
]

# Define the preamble that guides the AI model on how to categorize queries.
preamble = """ 
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook'.
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date data.
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date info.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram'.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go'.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate an image.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down.
-> Respond with 'content (topic)' if a query is asking to write content like applications, codes, emails, etc.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on Google.
-> Respond with 'youtube search (topic)' if a query is asking to search a topic on YouTube.
-> Respond with 'exit' if the user says goodbye or wants to end the conversation.
"""

# Define a chat history with predefined user-chatbot interactions for context.
ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "do you like pizza?"},
    {"role": "Chatbot", "message": "general do you like pizza?"},
    {"role": "User", "message": "open chrome and tell me about mahatma gandhi."},
    {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi."},
    {"role": "User", "message": "what is today's date and remind me I have a dancing performance on 5th Aug at 11pm"},
    {"role": "Chatbot", "message": "general what is today's date, reminder 11:00pm 5th Aug dancing performance"}
]

# Define the main function for decision-making on queries.


def FirstLayerDMM(prompt: str, recursion_depth: int = 3):
    if recursion_depth == 0:
        return ["general (uncategorized query)"]  # Prevent infinite recursion

    try:
        # Create a streaming chat session with the Cohere model.
        stream = co.chat_stream(
            model="command-r-plus",
            message=prompt,
            temperature=0.7,
            chat_history=ChatHistory,
            prompt_truncation="OFF",
            connectors=[],
            preamble=preamble
        )

        # Collect response text from the stream
        response = ""
        for event in stream:
            if event.event_type == "text-generation":
                response += event.text

        # Process response
        response = [task.strip() for task in response.replace(
            "\n", " ").split(".") if task.strip()]

        # Filter recognized functions
        response = [task for task in response if any(
            task.startswith(func) for func in funcs)]

        # Handle cases where model asks for clarification
        if "(query)" in response:
            return FirstLayerDMM(prompt=prompt, recursion_depth=recursion_depth - 1)

        return response

    except Exception as e:
        print(f"[bold red]Error:[/bold red] {e}")
        return ["general (error processing query)"]


# Entry point for the script.
if __name__ == "__main__":
    while True:
        user_input = input(">>> ").strip().lower()
        if user_input in ["exit", "quit", "bye"]:
            print("[bold green]Goodbye![/bold green] 👋")
            break

        response = FirstLayerDMM(user_input)
        print(response)
