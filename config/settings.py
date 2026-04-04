BROWSER = "chromium"
HEADLESS = False
TIMEOUT = 10000  # ms
SLOW_MO = 50
SCREENSHOTS = True

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Get OpenAI API key from environment
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
