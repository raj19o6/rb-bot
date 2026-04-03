#!/usr/bin/env python3
"""
Record a workflow by performing it manually in the browser.
"""
import sys
from engine.recorder import record_workflow

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\n" + "="*70)
        print("🎬 RB-BOT WORKFLOW RECORDER")
        print("="*70)
        print("\nUsage:")
        print("  python3 record_workflow.py <workflow_name> <starting_url>")
        print("\nExample:")
        print("  python3 record_workflow.py 'Login Flow' https://example.com/login")
        print("\nWhat happens:")
        print("  1. Browser opens at the starting URL")
        print("  2. You perform your workflow manually")
        print("  3. Bot records everything you do")
        print("  4. Press ENTER when done")
        print("  5. Confirm to save the workflow")
        print("\nThen you can replay it anytime!")
        print("="*70)
        sys.exit(1)
    
    workflow_name = sys.argv[1]
    base_url = sys.argv[2]
    
    record_workflow(workflow_name, base_url)
