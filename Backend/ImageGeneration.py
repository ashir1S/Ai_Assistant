import asyncio
import os
import sys
from random import randint
from pathlib import Path
from PIL import Image  # Keep PIL import if needed elsewhere, otherwise remove
import aiohttp
import logging
from dotenv import load_dotenv

# --- Helper function for PyInstaller resource path ---
def resource_path(relative_path: str) -> Path:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # Not running in a bundle, use the script's directory or project root
        # Adjust this if your script structure is different
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Environment Variable Loading ---
# Load .env file from the location determined by resource_path
# Ensure your .env file is included in your PyInstaller spec file (datas section)
try:
    # Attempt to load .env relative to the script/bundle
    dotenv_path = resource_path('.env')
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.warning(f".env file not found at expected location: {dotenv_path}")
        # Fallback: Check relative to the project root if needed (adjust logic)
        project_root_env = Path(__file__).resolve().parent.parent / '.env'
        if project_root_env.exists():
            load_dotenv(dotenv_path=project_root_env)
            logger.info(f"Loaded environment variables from project root: {project_root_env}")

except Exception as e:
    logger.error(f"Error loading .env file: {e}")

API_KEY = os.getenv("HuggingFaceAPIKey")
if not API_KEY:
    logger.warning("HuggingFaceAPIKey not found in environment variables.")

# --- API Configuration ---
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
HEADERS = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

# --- Path Handling (More Robust for PyInstaller) ---
# Determine the base directory: Use sys._MEIPASS if bundled, otherwise script's parent's parent
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running in a PyInstaller bundle
    PROJECT_ROOT = Path(sys._MEIPASS).resolve()
    logger.info(f"Running bundled. PROJECT_ROOT set to: {PROJECT_ROOT}")
    # Adjust paths if your data/frontend files are bundled differently
    # Example: If they are in the root of the bundle
    FRONTEND_DIR = PROJECT_ROOT / "Frontend"
    DATA_DIR = PROJECT_ROOT / "Data"
else:
    # Running as a normal script
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    logger.info(f"Running as script. PROJECT_ROOT set to: {PROJECT_ROOT}")
    FRONTEND_DIR = PROJECT_ROOT / "Frontend"
    DATA_DIR = PROJECT_ROOT / "Data"


# Define specific file paths based on the determined directories
FRONTEND_FILES_DIR = FRONTEND_DIR / "Files"
IMAGE_GENERATION_DATA_FILE = FRONTEND_FILES_DIR / "ImageGeneration.data"
GENERATED_IMAGE_DATA_FILE = FRONTEND_FILES_DIR / "GeneratedImage.data" # Path for the new status file

# --- Ensure Directories Exist ---
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FRONTEND_FILES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured directories exist: {DATA_DIR}, {FRONTEND_FILES_DIR}")
except Exception as e:
    logger.error(f"Failed to create directories: {e}")
    # Consider exiting or handling this error more gracefully depending on requirements
    sys.exit(1) # Exit if essential directories cannot be created

# --- Initialize Data File if Missing ---
if not IMAGE_GENERATION_DATA_FILE.exists():
    try:
        IMAGE_GENERATION_DATA_FILE.write_text("False,False", encoding='utf-8')
        logger.info(f"Initialized data file: {IMAGE_GENERATION_DATA_FILE}")
    except Exception as e:
        logger.error(f"Failed to initialize data file {IMAGE_GENERATION_DATA_FILE}: {e}")

# --- Core Asynchronous Functions ---
async def fetch_image(session: aiohttp.ClientSession, payload: dict, timeout: int = 120) -> bytes | None:
    """Send image generation request and return image bytes."""
    if not HEADERS:
        logger.error("API Key is missing. Cannot fetch image.")
        return None
    logger.info(f"Sending request to {API_URL} with payload keys: {payload.keys()}")
    try:
        async with session.post(API_URL, headers=HEADERS, json=payload, timeout=timeout) as resp:
            logger.info(f"API Response Status: {resp.status}")
            resp.raise_for_status()  # Raises exception for 4xx/5xx status codes
            image_bytes = await resp.read()
            logger.info(f"Received image data: {len(image_bytes)} bytes")
            return image_bytes
    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP Error during image generation: {e.status} {e.message}")
        # Attempt to read the response body for more details if available
        try:
            error_details = await e.response.text()
            logger.error(f"Error details from API: {error_details}")
        except Exception as read_err:
            logger.error(f"Could not read error details from response: {read_err}")
        return None
    except asyncio.TimeoutError:
        logger.error(f"Image generation request timed out after {timeout} seconds.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during image generation request: {e}", exc_info=True)
        return None

async def generate_images(prompt: str) -> list[Path]:
    """Generate and save images for a given prompt."""
    # Sanitize prompt for use in filename (basic example)
    prompt_slug = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in prompt)[:50] # Limit length
    saved_paths = []

    async with aiohttp.ClientSession() as session:
        seed = randint(0, 1_000_000)
        # Construct payload carefully
        payload = {
            "inputs": f"{prompt}, 4K, high resolution, ultra high details, sharp focus",
            "parameters": { # Use parameters for better control if API supports
                "seed": seed,
                "negative_prompt": "blurry, low quality, text, watermark, signature",
                 # Add other parameters as needed, e.g., guidance_scale, num_inference_steps
            },
            "options": { # Options if supported by API
                 "wait_for_model": True # Example option
            }
        }
        logger.info(f"Generating image with seed: {seed}")
        image_data = await fetch_image(session, payload)

        if image_data:
            try:
                # Use a unique filename, e.g., with timestamp or UUID if needed
                file_path = DATA_DIR / f"{prompt_slug}_{seed}.jpg"
                file_path.write_bytes(image_data)
                saved_paths.append(file_path)
                logger.info(f"Successfully saved image: {file_path}")
            except IOError as e:
                logger.error(f"Failed to save image {file_path}: {e}")
            except Exception as e:
                 logger.error(f"An unexpected error occurred during image saving: {e}", exc_info=True)

    return saved_paths

# --- MODIFIED FUNCTION ---
async def open_images(image_paths: list[Path]) -> None:
    """Write the first image path to status file instead of opening externally."""
    if image_paths:
        first_image_path = image_paths[0]
        try:
            # Write the full, absolute path to the status file
            GENERATED_IMAGE_DATA_FILE.write_text(str(first_image_path.resolve()), encoding='utf-8')
            logger.info(f"Image path written to status file: {GENERATED_IMAGE_DATA_FILE} -> {first_image_path}")
        except IOError as e:
            logger.error(f"Failed to write to status file {GENERATED_IMAGE_DATA_FILE}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred writing to status file: {e}", exc_info=True)
    else:
        logger.warning("No images were generated successfully to write to status file.")
        # Optionally, write an error status or clear the file
        try:
            GENERATED_IMAGE_DATA_FILE.write_text("ERROR: No image generated", encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write error status to file {GENERATED_IMAGE_DATA_FILE}: {e}")


async def generate_and_open_images(prompt: str) -> None:
    """End-to-end image generation and triggers the 'open' (write path) action."""
    if not API_KEY:
        logger.error("HuggingFace API key not configured. Cannot generate images.")
        # Update status file to indicate configuration error
        try:
            GENERATED_IMAGE_DATA_FILE.write_text("ERROR: API Key missing", encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write API key error status to file {GENERATED_IMAGE_DATA_FILE}: {e}")
        return

    logger.info(f"Starting image generation for prompt: '{prompt}'")
    images = await generate_images(prompt)

    # Call the modified open_images function (which now writes the path)
    await open_images(images) # Pass the list of generated paths

async def main() -> None:
    """Monitor the data file for generation requests."""
    logger.info("Image generation service started. Monitoring control file...")
    while True:
        try:
            # Check if the control file exists before reading
            if not IMAGE_GENERATION_DATA_FILE.exists():
                logger.warning(f"Control file not found: {IMAGE_GENERATION_DATA_FILE}. Waiting...")
                await asyncio.sleep(5) # Wait longer if file is missing
                continue

            # Read content with explicit encoding
            content = IMAGE_GENERATION_DATA_FILE.read_text(encoding='utf-8').strip()

            if not content or content == "False,False": # Check for initial/reset state
                await asyncio.sleep(1) # Short poll interval when idle
                continue

            # Parse request (handle potential variations like ';' or ',')
            # Prioritize ';' if present, otherwise use ','
            separator = ";" if ";" in content else ","
            parts = content.split(separator, 1)

            if len(parts) == 2:
                prompt, status = (p.strip() for p in parts)
                if status.lower() == "true":
                    logger.info(f"Received generation request. Prompt: '{prompt}'")
                    # Reset the control file *before* starting generation
                    # to prevent reprocessing the same request on restart
                    try:
                        IMAGE_GENERATION_DATA_FILE.write_text("False,False", encoding='utf-8')
                        logger.info(f"Reset control file: {IMAGE_GENERATION_DATA_FILE}")
                    except IOError as e:
                        logger.error(f"Failed to reset control file {IMAGE_GENERATION_DATA_FILE}: {e}")
                        # Decide if you should proceed or wait
                        await asyncio.sleep(5)
                        continue # Skip this cycle if control file can't be reset

                    # Start the generation process
                    await generate_and_open_images(prompt)
                    logger.info(f"Finished processing prompt: '{prompt}'")

                else:
                    # If status is not 'true', wait before checking again
                    await asyncio.sleep(1)
            else:
                logger.warning(f"Invalid data format in control file: '{content}'. Resetting file.")
                # Attempt to reset the file to a known state
                try:
                    IMAGE_GENERATION_DATA_FILE.write_text("False,False", encoding='utf-8')
                except IOError as e:
                    logger.error(f"Failed to reset invalid control file {IMAGE_GENERATION_DATA_FILE}: {e}")
                await asyncio.sleep(5) # Wait after finding invalid format

        except FileNotFoundError:
             logger.warning(f"Control file disappeared: {IMAGE_GENERATION_DATA_FILE}. Waiting...")
             await asyncio.sleep(5)
        except IOError as e:
            logger.error(f"I/O Error accessing control file {IMAGE_GENERATION_DATA_FILE}: {e}", exc_info=True)
            await asyncio.sleep(5) # Wait before retrying after IO errors
        except Exception as e:
            logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            # Consider adding a mechanism to prevent rapid looping on persistent errors
            await asyncio.sleep(10) # Longer wait for unexpected errors

if __name__ == "__main__":
    # Ensure the script handles KeyboardInterrupt gracefully
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Image generation service stopped by user.")
    except Exception as e:
        logger.critical(f"Critical error preventing service start: {e}", exc_info=True)
