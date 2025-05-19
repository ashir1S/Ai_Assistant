# RealtimeSearchEngine.py
import os
import sys
import io # Added for UTF-8 output handling

# --- UTF-8 Output Configuration ---
# Attempt to set console output to UTF-8, especially for Windows.
# This should be done as early as possible.
try:
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except (AttributeError, io.UnsupportedOperation) as e:
    # This can happen if not in a proper terminal (e.g., piped output on some OS)
    # or if buffer is not available. Silently pass or print a warning.
    # print(f"Notice: Could not reconfigure stdout/stderr encoding: {e}", file=sys.__stderr__) # Use original stderr
    pass
# --- End UTF-8 Output Configuration ---

from serpapi import GoogleSearch
from groq import Groq
from json import load, dump
import datetime
import pytz
from dotenv import load_dotenv
import platform

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# Load environment variables
load_dotenv(dotenv_path=resource_path('.env'))
Username      = os.getenv("Username", "User")
Assistantname = os.getenv("Assistantname", "Assistant")
GroqAPIKey    = os.getenv("GroqAPIKey")
SerpAPIKey    = os.getenv("SerpAPIKey")

if not GroqAPIKey:
    # Use original stderr if reconfigured one fails for some reason during early startup
    print("CRITICAL: Groq API key not found in environment variables. Please set GroqAPIKey in your .env file.", file=sys.__stderr__)
    sys.exit(1) # Exit if critical key is missing
if not SerpAPIKey:
    print("WARNING: SerpAPI key not found in environment variables. Search functionality will be disabled. Time queries will still work.", file=sys.__stderr__)

client = Groq(api_key=GroqAPIKey)

# System prompt
System = f"""Hello, I am {Username}. You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Always answer ONLY using the provided search results below. If the answer is not found in the results, respond: 'I could not find the answer in the latest search results.' ***
*** Provide answers in a professional way, with proper grammar and punctuation. ***
"""

# Chat log setup
chatlog_path = resource_path(os.path.join("Data", "ChatLog.json"))
os.makedirs(os.path.dirname(chatlog_path), exist_ok=True)
try:
    with open(chatlog_path, "r", encoding='utf-8') as f: # Specify encoding for reading
        messages_log = load(f)
except FileNotFoundError:
    with open(chatlog_path, "w", encoding='utf-8') as f: # Specify encoding for writing
        dump([], f)
    messages_log = []
except Exception as e: # Catch other potential errors like JSONDecodeError
    print(f"Warning: Could not load chat log, initializing fresh: {e}", file=sys.__stderr__)
    with open(chatlog_path, "w", encoding='utf-8') as f:
        dump([], f)
    messages_log = []


def truncate_text(text, max_length=1000):
    return text[:max_length] + "..." if len(text) > max_length else text

def is_time_query(q):
    ql = q.lower()
    return ("what" in ql and "time" in ql and " in " in ql and "is it" in ql) or \
           ("current time in " in ql) or \
           ("time in " in ql and ql.endswith("?")) or \
           ("time in " in ql and ql.endswith(".")) or \
           ("time is it in" in ql)

zones = {
    "india": "Asia/Kolkata", "new delhi": "Asia/Kolkata", "mumbai": "Asia/Kolkata",
    "kolkata": "Asia/Kolkata", "chennai": "Asia/Kolkata", "bangalore": "Asia/Kolkata",
    "new york": "America/New_York", "nyc": "America/New_York", "usa": "America/New_York",
    "washington dc": "America/New_York", "london": "Europe/London", "uk": "Europe/London",
    "los angeles": "America/Los_Angeles", "la": "America/Los_Angeles", "california": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles", "paris": "Europe/Paris", "france": "Europe/Paris",
    "berlin": "Europe/Berlin", "germany": "Europe/Berlin", "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo",
    "sydney": "Australia/Sydney", "melbourne": "Australia/Sydney", "australia": "Australia/Sydney",
    "beijing": "Asia/Shanghai", "china": "Asia/Shanghai", "moscow": "Europe/Moscow", "russia": "Europe/Moscow",
    "dubai": "Asia/Dubai", "uae": "Asia/Dubai", "toronto": "America/Toronto", "canada": "America/Toronto",
    "utc": "UTC", "gmt": "GMT"
}

def get_current_time(query):
    query_cleaned = query.strip("() ").lower()
    loc_part_extracted = "utc"
    if " in " in query_cleaned:
        parts = query_cleaned.split(" in ", 1)
        if len(parts) > 1:
            loc_part_extracted = parts[1].strip().rstrip("?.!")
    loc_cleaned_for_match = loc_part_extracted.replace("the ", "").replace(" city", "").replace(" right now", "").strip()
    tz_name = "UTC"
    matched_loc_key = None
    if loc_cleaned_for_match in zones:
        tz_name = zones[loc_cleaned_for_match]
        matched_loc_key = loc_cleaned_for_match
    else:
        for key in sorted(zones.keys(), key=len, reverse=True):
            if key in loc_cleaned_for_match:
                tz_name = zones[key]
                matched_loc_key = key
                break
    if matched_loc_key is None:
        try:
            potential_tz = loc_cleaned_for_match.replace(" ", "_").title()
            pytz.timezone(potential_tz) # Try to validate if it's a real timezone
            tz_name = potential_tz
            matched_loc_key = loc_cleaned_for_match # If it is, use it
        except pytz.exceptions.UnknownTimeZoneError:
            pass # If not, tz_name remains UTC or the previously matched one
    try:
        timezone_to_use = pytz.timezone(tz_name)
        display_location = matched_loc_key.title() if matched_loc_key else loc_part_extracted.title()
    except pytz.exceptions.UnknownTimeZoneError:
        timezone_to_use = pytz.timezone("UTC") # Fallback to UTC
        display_location = f"{loc_part_extracted.title()} (Region not recognized, showing UTC)"
    now = datetime.datetime.now(timezone_to_use)
    day_format = "%#d" if platform.system() == "Windows" else "%-d" # Windows uses #d, others use -d
    time_format_string = f"%I:%M %p on %A, %B {day_format}, %Y"
    return now.strftime(time_format_string) + f" ({timezone_to_use.zone})", display_location

def PerformGoogleSearch(query, max_results_chars=4000):
    if not SerpAPIKey:
        return "Error: SerpAPI key not found. Search functionality is disabled."
    print(f"Performing Google Search for: {query}")
    extracted_info = []
    try:
        params = {"q": query, "engine": "google", "api_key": SerpAPIKey, "num": 7} # Get up to 7 results
        results = GoogleSearch(params).get_dict()

        if "answer_box" in results:
            box = results["answer_box"]
            content = []
            if "title" in box: content.append(f"Title: {box['title']}")
            if "answer" in box: content.append(f"Direct Answer: {box['answer']}")
            elif "snippet" in box: content.append(f"Featured Snippet: {box['snippet']}")
            source = box.get("source")
            if isinstance(source, dict):
                name, link = source.get("name", ""), source.get("link", "")
                if name and link: content.append(f"Source: {name} ({link})")
                elif link: content.append(f"Source: {link}")
            elif isinstance(source, str): content.append(f"Source: {source}")
            if content: extracted_info.append("Answer Box Information:\n" + "\n".join(content))

        if "knowledge_graph" in results:
            kg = results["knowledge_graph"]
            content = []
            if "title" in kg: content.append(f"Title: {kg['title']}")
            if "description" in kg: content.append(f"Description: {kg['description']}")
            source = kg.get("source")
            if isinstance(source, dict):
                name, link = source.get("name"), source.get("link")
                if name and link: content.append(f"Source: {name} ({link})")
                elif link: content.append(f"Source: {link}")
            attrs = kg.get("attributes")
            if isinstance(attrs, dict):
                attr_list = [f"  {k.replace('_', ' ').title()}: {', '.join(str(v) for v in val) if isinstance(val, list) else val}" for k, val in attrs.items()]
                if attr_list: content.append("Attributes:\n" + "\n".join(attr_list))
            elif isinstance(attrs, list): # Handle cases where attributes might be a list of dicts
                attr_list = [f"  {item['attribute']}: {item['value']}" for item in attrs if isinstance(item, dict) and 'attribute' in item and 'value' in item]
                if attr_list: content.append("Attributes:\n" + "\n".join(attr_list))
            if content: extracted_info.append("Knowledge Graph Information:\n" + "\n".join(content))

        organic = results.get("organic_results", [])
        if organic:
            snippets = []
            for i, res in enumerate(organic[:3]): # Top 3 organic results
                title = res.get("title", "No Title")
                snippet_text = res.get("snippet", "")
                if not snippet_text and "snippet_highlighted_words" in res:
                    snippet_text = " ".join(res["snippet_highlighted_words"]) if isinstance(res["snippet_highlighted_words"], list) else res["snippet_highlighted_words"]
                if not snippet_text: snippet_text = "No snippet available."
                link, display_url = res.get("link", ""), res.get("displayed_link", "")
                source_line = f"Source: {link}" + (f" (Display: {display_url})" if display_url and display_url not in link else "")
                snippets.append(f"Result {i+1}:\nTitle: {title}\nSnippet: {snippet_text}\n{source_line}")
            if snippets: extracted_info.append("Organic Search Results:\n" + "\n\n".join(snippets))

        related_q = results.get("related_questions", []) # "People Also Ask"
        if related_q:
            paa = []
            for i, q_block in enumerate(related_q[:3]): # Top 3 PAA
                question = q_block.get("question", "")
                answer = q_block.get("snippet", q_block.get("answer", "No answer snippet.")) # some PAA use 'answer' key
                link = ""
                if "source" in q_block and isinstance(q_block["source"], dict): link = q_block["source"].get("link", "")
                elif "link" in q_block: link = q_block.get("link","") # Sometimes link is directly available
                entry = f"Related Question {i+1}: {question}\nAnswer: {answer}"
                if link: entry += f"\nSource: {link}"
                paa.append(entry)
            if paa: extracted_info.append("People Also Ask:\n" + "\n\n".join(paa))

        final_output = "\n\n---\n\n".join(extracted_info)
        if not final_output.strip(): return "I could not find any relevant information in the latest search results."

        if len(final_output) > max_results_chars:
            final_output = final_output[:max_results_chars] + "...\n[Search results truncated due to length]"
        return final_output

    except Exception as e:
        print(f"Error during Google Search: {e}", file=sys.__stderr__)
        import traceback
        traceback.print_exc(file=sys.__stderr__)
        return "Error performing search, please check logs."

def AnswerModifier(answer):
    lines = [line.strip() for line in answer.strip().split('\n')]
    return '\n'.join([line for line in lines if line]) # Remove empty lines

def RealtimeSearchEngine(prompt):
    global messages_log
    try: # Reload chat log at the beginning of each call
        with open(chatlog_path, "r", encoding='utf-8') as f:
            messages_log = load(f)
    except FileNotFoundError:
        messages_log = [] # Keep it empty if not found, will be created on save
    except Exception as e: # JSONDecodeError or other issues
        print(f"Warning: Could not reload chat log during request, using in-memory version: {e}", file=sys.__stderr__)
        # messages_log remains as it was in memory

    prompt_cleaned_for_time = prompt.strip("() ") # Clean for time query check
    if is_time_query(prompt_cleaned_for_time):
        time_str, display_location = get_current_time(prompt_cleaned_for_time)
        answer = f"The current time in {display_location} is {time_str}."
        messages_log.append({"role":"user", "content":prompt})
        messages_log.append({"role":"assistant", "content":answer})
        try:
            with open(chatlog_path,"w", encoding='utf-8') as f: dump(messages_log, f, indent=4)
        except Exception as e:
            print(f"Error saving chat log: {e}", file=sys.__stderr__)
        return AnswerModifier(answer)

    if not SerpAPIKey: # If SerpAPIKey is missing, cannot search
        answer = "I cannot perform web searches as the SerpAPI key is missing."
        messages_log.append({"role":"user", "content":prompt})
        messages_log.append({"role":"assistant","content":answer})
        try:
            with open(chatlog_path,"w", encoding='utf-8') as f: dump(messages_log, f, indent=4)
        except Exception as e:
            print(f"Error saving chat log: {e}", file=sys.__stderr__)
        return answer

    search_data = PerformGoogleSearch(prompt)
    # print(f"\n\nDEBUG: Data being sent to LLM:\n----------\n{search_data}\n----------\n\n") # For debugging search results
    
    # If search itself returned an error or no results, bypass LLM
    if "Error:" in search_data or "I could not find any relevant information" in search_data:
        messages_log.append({"role":"user", "content":prompt})
        messages_log.append({"role":"assistant","content":search_data}) # search_data is the error/message itself
        try:
            with open(chatlog_path,"w", encoding='utf-8') as f: dump(messages_log, f, indent=4)
        except Exception as e:
            print(f"Error saving chat log: {e}", file=sys.__stderr__)
        return AnswerModifier(search_data) # Return the search error/message

    # Prepare the content for the LLM
    search_message_content = (
        f"Based **ONLY** on the following search results, provide a comprehensive answer to the user's query.\n"
        f"If the information is not in the results, state that clearly: 'I could not find the answer in the latest search results.'\n"
        f"For data like stock prices or rapidly changing facts, acknowledge that the information reflects what was found in the search results at this moment.\n\n"
        f"User Query: \"{prompt}\"\n\n"
        f"Search Results:\n--------------------------------------------\n{search_data}\n--------------------------------------------\n\nYour Answer:"
    )
    
    # Construct conversation for Groq API
    # No need to include full history for this specific task, just system prompt and current query with search results.
    conversation = [{"role":"system","content":System}, {"role":"user", "content": search_message_content}]
    answer = ""
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192", # Specify the model
            messages=conversation,
            temperature=0.2, # Lower temperature for more factual answers
            max_tokens=2048, # Adjust as needed
            top_p=0.8,
            stream=True, # Enable streaming for faster perceived response
        )
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                answer += chunk.choices[0].delta.content
        answer = answer.strip().replace("</s>", "") # Clean up potential end-of-sequence tokens
        
        # Additional check to ensure the LLM adhered to the "not found" instruction
        if not answer.strip() or \
           "could not find the answer in the latest search results" in answer.lower() or \
           "not found in the provided search results" in answer.lower() or \
           "based on the provided search results, i cannot answer" in answer.lower() or \
           "information is not available in the provided search results" in answer.lower() or \
           "the provided search results do not contain information" in answer.lower(): # Added another common variation
            answer = "I could not find the answer in the latest search results."

    except Exception as e:
        print(f"Error during Groq API call: {e}", file=sys.__stderr__)
        import traceback
        traceback.print_exc(file=sys.__stderr__)
        answer = "Sorry, I encountered an error while processing your request with the AI model."

    # Log interaction and save
    messages_log.append({"role":"user", "content":prompt})
    messages_log.append({"role":"assistant","content":answer})
    try:
        with open(chatlog_path,"w", encoding='utf-8') as f: dump(messages_log, f, indent=4)
    except Exception as e:
        print(f"Error saving chat log: {e}", file=sys.__stderr__)
    return AnswerModifier(answer)

if __name__ == "__main__":
    print(f"Initializing {Assistantname}...")
    if not GroqAPIKey: # This check is already at the top, but good for emphasis if run directly
        print(f"{Assistantname}: CRITICAL ERROR - Groq API Key is not configured. The application cannot start.", file=sys.__stderr__)
        sys.exit(1)
    if not SerpAPIKey:
        print(f"{Assistantname}: WARNING - SerpAPI Key is not configured. Web search capabilities will be unavailable.", file=sys.__stderr__)
    
    print(f"--- {Assistantname} is ready. Type 'exit', 'quit', or 'bye' to end. ---")
    while True:
        try:
            prompt_input = input(f"{Username}: ")
        except UnicodeDecodeError:
            print(f"{Assistantname}: I had trouble understanding your input. Please ensure your terminal supports UTF-8 or avoid special characters.", file=sys.__stderr__)
            continue
        except KeyboardInterrupt: # Handle Ctrl+C gracefully
            print(f"\n{Assistantname}: Goodbye!")
            break

        if prompt_input.lower() in ['exit','quit','bye']:
            print(f"{Assistantname}: Goodbye!")
            break
        if not prompt_input.strip(): # Skip empty input
            continue
        
        response = RealtimeSearchEngine(prompt_input)
        print(f"{Assistantname}: {response}")