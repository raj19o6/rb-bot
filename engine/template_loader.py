import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def load(name: str, variables: dict) -> dict:
    path = TEMPLATES_DIR / f"{name}.json"
    raw = path.read_text()
    for k, v in variables.items():
        raw = raw.replace(f"{{{{{k}}}}}", str(v))
    return json.loads(raw)
