import asyncio
from random import randint
from pathlib import Path
from PIL import Image
import aiohttp
import logging
from dotenv import load_dotenv, get_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine project root directory (two levels up from this file)
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from project root .env
load_dotenv(dotenv_path=ROOT_DIR / ".env")
API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
API_KEY = get_key(str(ROOT_DIR / '.env'), 'HuggingFaceAPIKey')
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Paths relative to project root
DATA_DIR = ROOT_DIR / "Data"
FRONTEND_DATA_FILE = ROOT_DIR / "Frontend" / "Files" / "ImageGeneration.data"

# Ensure directories and data file exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
if not FRONTEND_DATA_FILE.exists():
    FRONTEND_DATA_FILE.write_text("False,False")

async def fetch_image(session: aiohttp.ClientSession, payload: dict, timeout: int = 60) -> bytes | None:
    """
    Send a single image generation request and return image bytes.
    """
    try:
        async with session.post(API_URL, headers=HEADERS, json=payload, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.read()
    except Exception as e:
        logger.error("Failed to fetch image: %s", e)
        return None

async def generate_images(prompt: str) -> list[Path]:
    """
    Generate 4 images for the given prompt and save them to disk.
    Returns a list of Paths to the saved images.
    """
    prompt_slug = prompt.replace(" ", "_")
    tasks = []
    async with aiohttp.ClientSession() as session:
        for _ in range(4):
            seed = randint(0, 1_000_000)
            payload = {
                "inputs": f"{prompt}, quality=4K, sharpness=maximum, Ultra High details, high resolution, seed={seed}"  # noqa: E501
            }
            tasks.append(fetch_image(session, payload))
        results = await asyncio.gather(*tasks)

    saved_paths = []
    for idx, data in enumerate(results, start=1):
        if data:
            file_path = DATA_DIR / f"{prompt_slug}{idx}.jpg"
            file_path.write_bytes(data)
            saved_paths.append(file_path)
            logger.info("Saved image: %s", file_path)
        else:
            logger.warning("Image %d for prompt '%s' failed to generate.", idx, prompt)
    return saved_paths

async def open_images(image_paths: list[Path]) -> None:
    """
    Open and display each image sequentially.
    """
    for path in image_paths:
        try:
            img = Image.open(path)
            img.show()
            logger.info("Displayed image: %s", path)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error("Unable to open image %s: %s", path, e)

async def generate_and_open_images(prompt: str) -> None:
    """
    High-level function to generate images for a prompt and display them.
    """
    images = await generate_images(prompt)
    if images:
        await open_images(images)
    else:
        logger.error("No images generated for prompt '%s'.", prompt)

async def main() -> None:
    """
    Main loop: watch the data file for a 'True' status and process requests.
    """
    while True:
        try:
            content = FRONTEND_DATA_FILE.read_text().strip()
            if not content:
                await asyncio.sleep(1)
                continue

            # Parse prompt and status
            if ";" in content:
                prompt, status = [c.strip() for c in content.split(";", 1)]
            elif "," in content:
                prompt, status = [c.strip() for c in content.split(",", 1)]
            else:
                logger.warning("Data file content malformed: '%s'", content)
                await asyncio.sleep(2)
                continue

            if status.lower() == "true":
                logger.info("Generating images for prompt: %s", prompt)
                await generate_and_open_images(prompt)
                FRONTEND_DATA_FILE.write_text("False,False")
                break
            else:
                await asyncio.sleep(1)
        except ValueError:
            logger.warning("Unable to parse prompt and status from data file.")
            await asyncio.sleep(2)
        except Exception:
            logger.exception("Error reading data file or processing request.")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
