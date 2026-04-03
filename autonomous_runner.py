"""
Autonomous runner - just provide URL and credentials, the bot does the rest.
"""
import json
from pathlib import Path
from core import browser
from engine.autonomous_agent import run_autonomous
from reports.html_reporter import generate
from engine.token_tracker import print_summary, save_session

CONFIG_FILE = Path(__file__).parent / "data" / "autonomous.json"


def run_autonomous_bot():
    """Run the bot in fully autonomous mode."""
    
    print("=" * 60)
    print("🤖 RB-BOT AUTONOMOUS MODE")
    print("=" * 60)
    
    # Load config
    config = json.loads(CONFIG_FILE.read_text())
    print(f"\n📋 Configuration loaded from: {CONFIG_FILE}")
    print(f"   Target: {config['base_url']}")
    print(f"   Username: {config['credentials'].get('username', 'N/A')}")
    
    page = browser.get_page()
    
    try:
        # Run autonomous agent
        results = run_autonomous(
            page=page,
            base_url=config["base_url"],
            credentials=config["credentials"],
            openai_api_key=config.get("openai_api_key")
        )
        
        # Generate reports
        print(f"\n📊 Generating reports...")
        generate(results["test_reports"], results["surf_reports"])
        
        # Save JSON
        output_dir = Path(__file__).parent / "reports"
        output_dir.mkdir(exist_ok=True)
        json_path = output_dir / "autonomous_report.json"
        json_path.write_text(json.dumps(results, indent=2))
        print(f"   JSON Report: {json_path}")
        
        print(f"\n✅ All done! Check reports/report.html")
        
        # Print token usage summary
        print_summary()
        save_session()
        
    finally:
        browser.close()


if __name__ == "__main__":
    run_autonomous_bot()
