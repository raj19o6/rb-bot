"""
Workflow Replay Engine - Executes recorded workflows.
Replays user-recorded actions with testing and security checks.
"""
import json
from pathlib import Path
from core import browser
from engine import executor
from security import headers, xss, sqli
from reports.html_reporter import generate
from engine.token_tracker import print_summary, save_session

WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"


class WorkflowPlayer:
    def __init__(self, page):
        self.page = page
        self.workflow = None
        self.results = []
        
    def load_workflow(self, workflow_path):
        """Load workflow from file."""
        if isinstance(workflow_path, str):
            workflow_path = Path(workflow_path)
        
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_path}")
        
        self.workflow = json.loads(workflow_path.read_text())
        print(f"\n  ✅ Loaded workflow: {self.workflow['name']}")
        print(f"     Total actions: {self.workflow['total_actions']}")
        return self.workflow
    
    def replay(self, test_data=None):
        """
        Replay the workflow.
        
        Args:
            test_data: Optional dict to override recorded values
                      e.g., {"username": "testuser", "password": "testpass"}
        """
        print("\n" + "="*70)
        print("▶️  REPLAYING WORKFLOW")
        print("="*70)
        print(f"  Workflow: {self.workflow['name']}")
        print(f"  Actions: {len(self.workflow['actions'])}")
        if test_data:
            print(f"  Test Data: {list(test_data.keys())}")
        print("="*70)
        
        actions = self.workflow['actions']
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('action')
            
            try:
                print(f"\n  [{i}/{len(actions)}] {action_type.upper()}", end="")
                
                if action_type == 'goto':
                    url = action['url']
                    print(f" → {url}")
                    self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    self.page.wait_for_timeout(500)
                    self.results.append({"action": action, "status": "pass"})
                
                elif action_type == 'fill':
                    selector = action['selector']
                    value = action['value']
                    
                    # Override with test data if provided
                    if test_data:
                        for key, test_value in test_data.items():
                            if key.lower() in selector.lower():
                                value = test_value
                                break
                    
                    print(f" {selector} → {value[:30]}")
                    
                    locator = self.page.locator(selector)
                    if locator.is_visible(timeout=2000):
                        locator.fill(value, timeout=5000)
                        self.results.append({"action": action, "status": "pass"})
                    else:
                        print(" (element not visible, skipped)")
                        self.results.append({"action": action, "status": "skip", "reason": "not visible"})
                
                elif action_type == 'click':
                    selector = action['selector']
                    text = action.get('text', '')[:30]
                    print(f" {selector} ({text})")
                    
                    locator = self.page.locator(selector)
                    if locator.is_visible(timeout=2000):
                        # Check if this might cause navigation
                        is_submit = 'submit' in selector.lower() or 'button' in text.lower()
                        
                        if is_submit:
                            try:
                                with self.page.expect_navigation(timeout=10000):
                                    locator.click(timeout=5000)
                                self.page.wait_for_load_state("networkidle", timeout=10000)
                                print("     (navigation completed)")
                            except:
                                locator.click(timeout=5000)
                                self.page.wait_for_timeout(1000)
                        else:
                            locator.click(timeout=5000)
                            self.page.wait_for_timeout(500)
                        
                        self.results.append({"action": action, "status": "pass"})
                    else:
                        print(" (element not visible, skipped)")
                        self.results.append({"action": action, "status": "skip", "reason": "not visible"})
                
                elif action_type == 'submit':
                    selector = action['selector']
                    print(f" {selector}")
                    
                    locator = self.page.locator(selector)
                    if locator.is_visible(timeout=2000):
                        try:
                            with self.page.expect_navigation(timeout=10000):
                                locator.evaluate("form => form.submit()")
                            self.page.wait_for_load_state("networkidle", timeout=10000)
                        except:
                            locator.evaluate("form => form.submit()")
                            self.page.wait_for_timeout(2000)
                        
                        self.results.append({"action": action, "status": "pass"})
                    else:
                        print(" (form not visible, skipped)")
                        self.results.append({"action": action, "status": "skip", "reason": "not visible"})
                
            except Exception as e:
                print(f" ❌ FAILED: {e}")
                self.results.append({"action": action, "status": "fail", "error": str(e)})
        
        print("\n" + "="*70)
        print("✅ REPLAY COMPLETED")
        print("="*70)
        
        return self.results
    
    def run_security_checks(self):
        """Run security checks on current page."""
        print("\n  🔒 Running security checks...")
        
        security_findings = []
        
        try:
            security_findings += headers.check(self.page)
        except Exception as e:
            print(f"     ⚠️  Header check failed: {e}")
        
        try:
            security_findings += xss.check(self.page)
        except Exception as e:
            print(f"     ⚠️  XSS check failed: {e}")
        
        try:
            security_findings += sqli.check(self.page)
        except Exception as e:
            print(f"     ⚠️  SQLi check failed: {e}")
        
        print(f"     Found {len(security_findings)} security issues")
        return security_findings
    
    def get_summary(self):
        """Get replay summary."""
        passed = sum(1 for r in self.results if r["status"] == "pass")
        failed = sum(1 for r in self.results if r["status"] == "fail")
        skipped = sum(1 for r in self.results if r["status"] == "skip")
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped
        }


def replay_workflow(workflow_name, test_data=None, run_security=True):
    """
    Replay a recorded workflow.
    
    Args:
        workflow_name: Name of the workflow file (without .json)
        test_data: Optional dict to override values
        run_security: Whether to run security checks
    """
    print("\n" + "="*70)
    print("🎬 RB-BOT WORKFLOW REPLAY")
    print("="*70)
    
    # Find workflow file
    workflow_file = WORKFLOWS_DIR / f"{workflow_name}.json"
    if not workflow_file.exists():
        print(f"  ❌ Workflow not found: {workflow_file}")
        print(f"\n  Available workflows:")
        for wf in WORKFLOWS_DIR.glob("*.json"):
            print(f"    - {wf.stem}")
        return None
    
    page = browser.get_page()
    player = WorkflowPlayer(page)
    
    try:
        # Load workflow
        player.load_workflow(workflow_file)
        
        # Replay
        results = player.replay(test_data)
        
        # Security checks
        security_findings = []
        if run_security:
            security_findings = player.run_security_checks()
        
        # Summary
        summary = player.get_summary()
        
        print("\n" + "="*70)
        print("📊 REPLAY SUMMARY")
        print("="*70)
        print(f"  Total Actions:     {summary['total']}")
        print(f"  Passed:            {summary['passed']}")
        print(f"  Failed:            {summary['failed']}")
        print(f"  Skipped:           {summary['skipped']}")
        print(f"  Security Issues:   {len(security_findings)}")
        print("="*70)
        
        # Generate report
        report = {
            "template": workflow_name,
            "url": player.workflow['actions'][0].get('url', 'N/A') if player.workflow['actions'] else 'N/A',
            "timestamp": player.workflow['created'],
            "steps": [{"step": r["action"], "status": r["status"], "error": r.get("error", "")} for r in results],
            "validations": [],
            "security": {
                "critical": [f for f in security_findings if f.get("severity") == "critical"],
                "high": [f for f in security_findings if f.get("severity") == "high"],
                "medium": [f for f in security_findings if f.get("severity") == "medium"],
                "low": [f for f in security_findings if f.get("severity") == "low"],
            },
            "security_testcases": [],
            "elements": [],
            "summary": {
                "total": summary['total'],
                "passed": summary['passed'],
                "failed": summary['failed'],
                "security_issues": len(security_findings)
            }
        }
        
        # Generate HTML report
        generate([report], [])
        
        print(f"\n  📄 Report generated: reports/report.html")
        
        # Token summary if AI was used
        print_summary()
        save_session()
        
        return report
        
    finally:
        browser.close()


def list_workflows():
    """List all available workflows."""
    print("\n" + "="*70)
    print("📋 AVAILABLE WORKFLOWS")
    print("="*70)
    
    workflows = list(WORKFLOWS_DIR.glob("*.json"))
    
    if not workflows:
        print("  No workflows found.")
        print(f"  Record one using: python record_workflow.py")
        return
    
    for wf in workflows:
        try:
            data = json.loads(wf.read_text())
            print(f"\n  📁 {wf.stem}")
            print(f"     Name: {data['name']}")
            print(f"     Actions: {data['total_actions']}")
            print(f"     Created: {data['created']}")
        except:
            print(f"\n  📁 {wf.stem} (corrupted)")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  List workflows:  python replay.py list")
        print("  Replay workflow: python replay.py <workflow_name>")
        print("\nExample:")
        print("  python replay.py login_flow")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_workflows()
    else:
        workflow_name = command
        replay_workflow(workflow_name)
