#!/usr/bin/env python3
"""Quick test to verify login navigation works"""

import json
from pathlib import Path
from core import browser
from engine.autonomous_agent import run_autonomous

config_file = Path(__file__).parent / "data" / "autonomous.json"
config = json.loads(config_file.read_text())

print("Testing login navigation...")
print(f"URL: {config['base_url']}")
print(f"Username: {config['credentials']['username']}")

page = browser.get_page()

try:
    result = run_autonomous(
        page=page,
        base_url=config["base_url"],
        credentials=config["credentials"],
        openai_api_key=None  # Skip AI for faster testing
    )
    
    print("\n" + "="*60)
    print("RESULTS:")
    print(f"  Login successful: {result.get('login_successful', False)}")
    print(f"  Routes discovered: {len(result.get('test_reports', []))}")
    print("="*60)
    
finally:
    browser.close()
