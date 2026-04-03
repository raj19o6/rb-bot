"""
Codegen wrapper — launches Playwright codegen to record user actions
and saves the output as a reusable JSON template.

Usage:
    python3 codegen.py https://example.com --name login_test
"""

import subprocess
import sys
import json
import re
import argparse
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def run_codegen(url: str, template_name: str):
    """Launch playwright codegen, capture Python output, convert to JSON template."""
    output_py = Path(f"/tmp/{template_name}_codegen.py")

    print(f"[codegen] Launching browser for: {url}")
    print("[codegen] Perform your actions in the browser, then close it.")
    print(f"[codegen] Output will be saved to: templates/{template_name}.json\n")

    # Run playwright codegen — records actions into a Python script
    result = subprocess.run(
        ["python3", "-m", "playwright", "codegen", "--output", str(output_py), url],
        check=False,
    )

    if not output_py.exists():
        print("[codegen] No output recorded. Exiting.")
        sys.exit(1)

    raw = output_py.read_text()
    steps, validations = parse_codegen_output(raw)

    template = {
        "name": template_name,
        "steps": steps,
        "validations": validations,
    }

    out_path = TEMPLATES_DIR / f"{template_name}.json"
    out_path.write_text(json.dumps(template, indent=2))
    print(f"\n[codegen] ✅ Template saved: {out_path}")
    output_py.unlink(missing_ok=True)


def parse_codegen_output(code: str) -> tuple[list, list]:
    """
    Convert Playwright Python codegen output → our JSON step format.
    Extracts: goto, click (with xpath/css), fill, press.
    """
    steps = []
    validations = []

    for line in code.splitlines():
        line = line.strip()

        # goto
        m = re.search(r'page\.goto\("([^"]+)"\)', line)
        if m:
            steps.append({"action": "goto", "url": m.group(1)})
            continue

        # click — prefer xpath, fallback to css selector
        m = re.search(r'page\.(?:get_by_role|locator)\(([^)]+)\)\.click\(\)', line)
        if m:
            selector = _extract_selector(m.group(1))
            steps.append({"action": "click", "selector": selector})
            continue

        # fill
        m = re.search(r'page\.(?:get_by_role|locator)\(([^)]+)\)\.fill\("([^"]*)"\)', line)
        if m:
            selector = _extract_selector(m.group(1))
            steps.append({"action": "fill", "selector": selector, "value": m.group(2)})
            continue

        # press (keyboard)
        m = re.search(r'page\.(?:get_by_role|locator)\(([^)]+)\)\.press\("([^"]*)"\)', line)
        if m:
            selector = _extract_selector(m.group(1))
            steps.append({"action": "press", "selector": selector, "key": m.group(2)})
            continue

        # expect URL
        m = re.search(r'expect\(page\)\.to_have_url\(re\.compile\("([^"]+)"\)\)', line)
        if m:
            validations.append({"type": "url_contains", "value": m.group(1)})
            continue

        m = re.search(r'expect\(page\)\.to_have_url\("([^"]+)"\)', line)
        if m:
            validations.append({"type": "url_contains", "value": m.group(1)})

    return steps, validations


def _extract_selector(raw: str) -> str:
    """
    Prefer xpath selectors from codegen output.
    Falls back to the raw string if no xpath found.
    """
    # xpath explicitly passed
    m = re.search(r'"(xpath=//[^"]+)"', raw)
    if m:
        return m.group(1)

    # locator with xpath string
    m = re.search(r'"(//[^"]+)"', raw)
    if m:
        return f"xpath={m.group(1)}"

    # css selector string
    m = re.search(r'"([^"]+)"', raw)
    if m:
        return m.group(1)

    return raw.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record a test template via Playwright codegen")
    parser.add_argument("url", help="URL to open in codegen browser")
    parser.add_argument("--name", default="recorded_test", help="Template name (no .json)")
    args = parser.parse_args()
    run_codegen(args.url, args.name)
