"""
Batch runner for testing multiple websites at scale.
Supports testing 1000s of websites with cost tracking.
"""
import json
from pathlib import Path
from datetime import datetime
from core import browser
from engine.autonomous_agent import run_autonomous
from reports.html_reporter import generate
from engine.token_tracker import get_tracker, print_summary, save_session

BATCH_CONFIG = Path(__file__).parent / "data" / "batch_websites.json"


def run_batch():
    """Run autonomous tests on multiple websites."""
    
    # Load batch configuration
    if not BATCH_CONFIG.exists():
        print(f"❌ Batch config not found: {BATCH_CONFIG}")
        print(f"   Create a file with this structure:")
        print("""
{
  "openai_api_key": "sk-...",
  "websites": [
    {
      "name": "Website 1",
      "base_url": "https://example1.com/login",
      "credentials": {
        "username": "user1",
        "password": "pass1"
      }
    },
    {
      "name": "Website 2",
      "base_url": "https://example2.com",
      "credentials": {
        "username": "user2",
        "password": "pass2"
      }
    }
  ]
}
        """)
        return
    
    config = json.loads(BATCH_CONFIG.read_text())
    websites = config.get("websites", [])
    openai_key = config.get("openai_api_key")
    
    print("="*70)
    print("🚀 BATCH AUTONOMOUS TESTING")
    print("="*70)
    print(f"  Total websites to test: {len(websites)}")
    print(f"  OpenAI API: {'Enabled' if openai_key else 'Disabled'}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    results = []
    
    for i, site in enumerate(websites, 1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(websites)}] Testing: {site['name']}")
        print(f"{'='*70}")
        
        page = browser.get_page()
        
        try:
            result = run_autonomous(
                page=page,
                base_url=site["base_url"],
                credentials=site.get("credentials", {}),
                openai_api_key=openai_key
            )
            
            # Generate individual report
            report_dir = Path(__file__).parent / "reports" / "batch" / site["name"].replace(" ", "_")
            report_dir.mkdir(parents=True, exist_ok=True)
            
            # Save HTML report
            html_path = report_dir / "report.html"
            generate(result["test_reports"], result["surf_reports"])
            
            # Move report to batch folder
            default_report = Path(__file__).parent / "reports" / "report.html"
            if default_report.exists():
                default_report.rename(html_path)
            
            # Save JSON
            json_path = report_dir / "results.json"
            json_path.write_text(json.dumps(result, indent=2))
            
            results.append({
                "name": site["name"],
                "url": site["base_url"],
                "status": "success",
                "routes_tested": len(result["test_reports"]),
                "security_issues": sum(r["summary"]["security_issues"] for r in result["test_reports"]),
                "report_path": str(html_path)
            })
            
            print(f"\n✅ {site['name']} completed successfully")
            
        except Exception as e:
            print(f"\n❌ {site['name']} failed: {e}")
            results.append({
                "name": site["name"],
                "url": site["base_url"],
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            browser.close()
    
    # ═══════════════════════════════════════════════════════════════════════
    # Final Summary
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "="*70)
    print("📊 BATCH TEST SUMMARY")
    print("="*70)
    
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "failed"]
    
    print(f"  Total Websites:      {len(websites)}")
    print(f"  Successful:          {len(successful)}")
    print(f"  Failed:              {len(failed)}")
    print(f"  Total Routes Tested: {sum(r.get('routes_tested', 0) for r in successful)}")
    print(f"  Total Security Issues: {sum(r.get('security_issues', 0) for r in successful)}")
    print("="*70)
    
    # Show individual results
    print("\n📋 Individual Results:")
    print("-"*70)
    for r in results:
        status_icon = "✅" if r["status"] == "success" else "❌"
        print(f"  {status_icon} {r['name']}")
        if r["status"] == "success":
            print(f"      Routes: {r['routes_tested']}, Security Issues: {r['security_issues']}")
            print(f"      Report: {r['report_path']}")
        else:
            print(f"      Error: {r.get('error', 'Unknown')}")
    print("-"*70)
    
    # Print token usage summary
    print_summary()
    save_session()
    
    # Save batch summary
    summary_path = Path(__file__).parent / "reports" / "batch" / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_websites": len(websites),
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
        "token_usage": get_tracker().get_session_summary()
    }, indent=2))
    
    print(f"\n📄 Batch summary saved: {summary_path}")
    print(f"\n✅ Batch testing complete!")


if __name__ == "__main__":
    run_batch()
