BROWSER = "chromium"
HEADLESS = False
TIMEOUT = 10000  # ms
SLOW_MO = 50
SCREENSHOTS = True

import json
from pathlib import Path

_input = json.loads((Path(__file__).parent.parent / "data" / "input.json").read_text())
OPENAI_API_KEY: str = _input.get("openai_api_key", "")
