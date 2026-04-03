#!/usr/bin/env python3
"""
Replay a recorded workflow with testing and security checks.
"""
import sys
from engine.replay import replay_workflow, list_workflows

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n" + "="*70)
        print("▶️  RB-BOT WORKFLOW REPLAY")
        print("="*70)
        print("\nUsage:")
        print("  python3 replay_workflow.py <workflow_name>")
        print("  python3 replay_workflow.py list")
        print("\nExample:")
        print("  python3 replay_workflow.py login_flow")
        print("\nWhat happens:")
        print("  1. Bot loads the recorded workflow")
        print("  2. Replays all actions automatically")
        print("  3. Runs security checks (XSS, SQLi, Headers)")
        print("  4. Generates HTML report")
        print("  5. Shows cost summary")
        print("="*70)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_workflows()
    else:
        workflow_name = command
        replay_workflow(workflow_name)
