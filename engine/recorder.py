"""
Workflow Recorder - Records user actions in real-time.
Captures clicks, fills, navigation, and creates replayable workflows.
"""
import json
from pathlib import Path
from datetime import datetime
from core import browser

WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"
WORKFLOWS_DIR.mkdir(exist_ok=True)


class WorkflowRecorder:
    def __init__(self, page):
        self.page = page
        self.actions = []
        self.start_time = None
        self.workflow_name = None
        
    def start_recording(self, workflow_name):
        """Start recording user actions."""
        self.workflow_name = workflow_name
        self.start_time = datetime.now()
        self.actions = []
        
        print("\n" + "="*70)
        print("🎬 RECORDING STARTED")
        print("="*70)
        print(f"  Workflow: {workflow_name}")
        print(f"  Started: {self.start_time.strftime('%H:%M:%S')}")
        print("\n  Perform your workflow now...")
        print("  I'm watching and recording everything!")
        print("="*70)
        
        # Inject recording script into page
        self._inject_recorder()
    
    def _inject_recorder(self):
        """Inject JavaScript to capture user interactions."""
        recorder_script = """
        window.__rb_actions = [];
        
        // Record clicks
        document.addEventListener('click', (e) => {
            const target = e.target;
            const selector = getSelector(target);
            const text = target.innerText?.substring(0, 50) || '';
            const tag = target.tagName.toLowerCase();
            
            window.__rb_actions.push({
                type: 'click',
                selector: selector,
                text: text,
                tag: tag,
                timestamp: Date.now()
            });
        }, true);
        
        // Record input changes
        document.addEventListener('input', (e) => {
            const target = e.target;
            const selector = getSelector(target);
            const value = target.value;
            const inputType = target.type || 'text';
            
            window.__rb_actions.push({
                type: 'fill',
                selector: selector,
                value: value,
                inputType: inputType,
                timestamp: Date.now()
            });
        }, true);
        
        // Record form submissions
        document.addEventListener('submit', (e) => {
            const form = e.target;
            const selector = getSelector(form);
            
            window.__rb_actions.push({
                type: 'submit',
                selector: selector,
                timestamp: Date.now()
            });
        }, true);
        
        // Helper to generate CSS selector
        function getSelector(el) {
            if (el.id) return '#' + el.id;
            if (el.name) return `[name="${el.name}"]`;
            if (el.className && typeof el.className === 'string') {
                const classes = el.className.trim().split(/\\s+/).slice(0, 2).join('.');
                if (classes) return el.tagName.toLowerCase() + '.' + classes;
            }
            return el.tagName.toLowerCase();
        }
        
        console.log('🎬 Recorder injected and ready!');
        """
        
        try:
            self.page.evaluate(recorder_script)
        except Exception as e:
            print(f"  ⚠️  Could not inject recorder: {e}")
    
    def capture_navigation(self, url):
        """Manually capture navigation events."""
        self.actions.append({
            "action": "goto",
            "url": url,
            "timestamp": datetime.now().isoformat()
        })
        print(f"  ✅ Recorded: goto {url}")
    
    def get_recorded_actions(self):
        """Get actions recorded by JavaScript."""
        try:
            js_actions = self.page.evaluate("window.__rb_actions || []")
            return js_actions
        except:
            return []
    
    def stop_recording(self):
        """Stop recording and process actions."""
        print("\n" + "="*70)
        print("⏹️  STOPPING RECORDING...")
        print("="*70)
        
        # Get JavaScript recorded actions
        js_actions = self.get_recorded_actions()
        
        # Process and deduplicate actions
        processed_actions = self._process_actions(js_actions)
        
        # Add to main actions list
        self.actions.extend(processed_actions)
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print(f"\n  Total actions recorded: {len(self.actions)}")
        print(f"  Duration: {duration:.1f} seconds")
        print("="*70)
        
        return self.actions
    
    def _process_actions(self, js_actions):
        """Process and clean up recorded actions."""
        processed = []
        last_fill = {}
        
        for action in js_actions:
            action_type = action.get('type')
            
            if action_type == 'click':
                processed.append({
                    "action": "click",
                    "selector": action['selector'],
                    "text": action.get('text', ''),
                    "tag": action.get('tag', '')
                })
                print(f"  ✅ Recorded: click {action['selector']} ({action.get('text', '')[:30]})")
            
            elif action_type == 'fill':
                selector = action['selector']
                value = action['value']
                
                # Deduplicate - only keep last value for each field
                if selector in last_fill:
                    # Update existing
                    for p in processed:
                        if p.get('action') == 'fill' and p.get('selector') == selector:
                            p['value'] = value
                            break
                else:
                    # Add new
                    processed.append({
                        "action": "fill",
                        "selector": selector,
                        "value": value,
                        "inputType": action.get('inputType', 'text')
                    })
                    print(f"  ✅ Recorded: fill {selector} → {value[:30] if len(value) > 30 else value}")
                
                last_fill[selector] = value
            
            elif action_type == 'submit':
                processed.append({
                    "action": "submit",
                    "selector": action['selector']
                })
                print(f"  ✅ Recorded: submit {action['selector']}")
        
        return processed
    
    def save_workflow(self):
        """Save recorded workflow to file."""
        if not self.actions:
            print("  ⚠️  No actions to save!")
            return None
        
        workflow = {
            "name": self.workflow_name,
            "created": self.start_time.isoformat(),
            "total_actions": len(self.actions),
            "actions": self.actions,
            "metadata": {
                "recorded_by": "rb-bot-recorder",
                "version": "1.0"
            }
        }
        
        # Save to file
        filename = f"{self.workflow_name.replace(' ', '_').lower()}.json"
        filepath = WORKFLOWS_DIR / filename
        filepath.write_text(json.dumps(workflow, indent=2))
        
        print(f"\n  💾 Workflow saved: {filepath}")
        return filepath
    
    def show_summary(self):
        """Show summary of recorded actions."""
        print("\n" + "="*70)
        print("📋 RECORDED WORKFLOW SUMMARY")
        print("="*70)
        
        action_types = {}
        for action in self.actions:
            action_type = action.get('action', 'unknown')
            action_types[action_type] = action_types.get(action_type, 0) + 1
        
        print(f"  Workflow: {self.workflow_name}")
        print(f"  Total Actions: {len(self.actions)}")
        print(f"\n  Breakdown:")
        for action_type, count in action_types.items():
            print(f"    - {action_type}: {count}")
        
        print("\n  Actions:")
        for i, action in enumerate(self.actions, 1):
            action_type = action.get('action')
            if action_type == 'goto':
                print(f"    {i}. goto → {action['url']}")
            elif action_type == 'fill':
                value = action['value'][:30] + "..." if len(action['value']) > 30 else action['value']
                print(f"    {i}. fill {action['selector']} → {value}")
            elif action_type == 'click':
                text = action.get('text', '')[:30]
                print(f"    {i}. click {action['selector']} ({text})")
            elif action_type == 'submit':
                print(f"    {i}. submit {action['selector']}")
        
        print("="*70)


def record_workflow(workflow_name, base_url):
    """
    Interactive workflow recorder.
    Opens browser and records user actions.
    """
    print("\n" + "="*70)
    print("🎬 RB-BOT WORKFLOW RECORDER")
    print("="*70)
    print(f"  Workflow: {workflow_name}")
    print(f"  Starting URL: {base_url}")
    print("="*70)
    
    page = browser.get_page()
    recorder = WorkflowRecorder(page)
    
    try:
        # Start recording
        recorder.start_recording(workflow_name)
        
        # Navigate to starting URL
        print(f"\n  🌐 Navigating to {base_url}...")
        page.goto(base_url, wait_until="domcontentloaded")
        recorder.capture_navigation(base_url)
        
        # Re-inject recorder after navigation
        recorder._inject_recorder()
        
        print("\n" + "="*70)
        print("  ⏸️  PERFORM YOUR WORKFLOW NOW")
        print("="*70)
        print("  - Login to the application")
        print("  - Navigate through pages")
        print("  - Fill forms")
        print("  - Click buttons")
        print("  - Do whatever you want to test")
        print("\n  When done, press ENTER in this terminal...")
        print("="*70)
        
        # Wait for user to finish
        input()
        
        # Stop recording
        actions = recorder.stop_recording()
        
        # Show summary
        recorder.show_summary()
        
        # Ask for confirmation
        print("\n" + "="*70)
        confirm = input("  💾 Save this workflow? (yes/no): ").strip().lower()
        
        if confirm in ['yes', 'y']:
            filepath = recorder.save_workflow()
            print(f"\n  ✅ Workflow saved successfully!")
            print(f"  📁 Location: {filepath}")
            print(f"\n  You can now replay this workflow anytime!")
            return filepath
        else:
            print("\n  ❌ Workflow discarded.")
            return None
        
    finally:
        browser.close()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python recorder.py <workflow_name> <base_url>")
        print("Example: python recorder.py 'Login Flow' https://example.com/login")
        sys.exit(1)
    
    workflow_name = sys.argv[1]
    base_url = sys.argv[2]
    
    record_workflow(workflow_name, base_url)
