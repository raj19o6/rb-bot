#!/usr/bin/env python3
"""
Chrome Recording Runner - Execute Chrome extension recordings with security testing
"""
import json
import sys
import os
import random
import time
from pathlib import Path
from core import browser
from core.logger import log
from security import headers, xss, sqli
from security import advanced as advanced_security
from engine import qa_checks
from engine.grc_report import generate_grc_report, save_grc_report
from reports import html_reporter
from engine.ai_testgen import generate_security_testcases
from engine.token_tracker import print_summary, save_session
from config.settings import GROQ_API_KEY
from datetime import datetime
import requests

def load_chrome_recording(recording_file):
    """Load Chrome extension recording"""
    with open(recording_file, 'r') as f:
        return json.load(f)

def execute_chrome_recording(recording_file, callback_url=None):
    """Execute Chrome extension recording with security testing"""
    
    print("="*70)
    print("🤖 CHROME RECORDING RUNNER WITH SECURITY TESTING")
    print("="*70)
    
    recording = load_chrome_recording(recording_file)
    workflow_id = os.getenv('WORKFLOW_ID', 'N/A')
    
    print(f"\nWorkflow: {recording.get('workflowName', 'Untitled')}")
    print(f"Workflow ID: {workflow_id}")
    print(f"Actions: {recording.get('actionCount', 0)}")
    print(f"Recorded: {recording.get('recordedAt', 'N/A')}")
    if callback_url:
        print(f"Callback URL: {callback_url}")
    print("-"*70)
    
    actions = recording.get('actions', [])
    if not actions:
        print("Error: No actions found in recording")
        return False
    
    base_url = actions[0].get('url')
    print(f"Starting URL: {base_url}")
    
    page = browser.get_page()
    
    step_results = []
    security_findings = []
    
    try:
        print(f"\nNavigating to: {base_url}")
        page.goto(base_url, wait_until='domcontentloaded', timeout=60000)
        # Human-like: random delay after page load
        page.wait_for_timeout(random.randint(2000, 4000))
        # Human-like: random mouse movement
        page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        page.wait_for_timeout(random.randint(500, 1500))
        
        print("\n"+"="*70)
        print("🎬 EXECUTING RECORDED WORKFLOW")
        print("="*70)
        
        for idx, action in enumerate(actions, 1):
            action_type = action.get('type')
            selector = action.get('selector')
            
            print(f"\n[{idx}/{len(actions)}] {action_type.upper()}: {selector[:60]}")
            
            try:
                status = 'pass'
                error = None
                
                clean_selector = selector
                if '[&' in selector or 'has-[' in selector:
                    if action_type == 'click' and action.get('text'):
                        text = action.get('text', '').strip()
                        if text and len(text) < 50:
                            clean_selector = f'button:has-text("{text}")'
                            print(f"  Using text selector: {clean_selector}")
                    else:
                        status = 'skip'
                        error = f'Invalid selector'
                        print(f"  SKIPPED: {error}")
                        step_results.append({
                            'step': {'action': action_type, 'selector': selector},
                            'status': status,
                            'error': error
                        })
                        continue
                
                if action_type == 'click':
                    text = action.get('text', '').strip()
                    if text and len(text) < 50 and ('group.flex' in selector or 'truncate' in selector or 'flex-1' in selector):
                        if selector.startswith('a'):
                            clean_selector = f'a:has-text("{text}")'
                        elif selector.startswith('button'):
                            clean_selector = f'button:has-text("{text}")'
                        elif selector.startswith('span'):
                            clean_selector = f'span:has-text("{text}")'
                        else:
                            clean_selector = f':has-text("{text}")'
                        print(f"  Using text selector: {clean_selector}")
                    
                    locator = page.locator(clean_selector)
                    
                    if not locator.is_visible(timeout=5000):
                        status = 'fail'
                        error = 'Element not visible'
                    else:
                        # Human-like: move mouse to element before clicking
                        try:
                            box = locator.bounding_box()
                            if box:
                                page.mouse.move(
                                    box['x'] + box['width'] / 2 + random.randint(-5, 5),
                                    box['y'] + box['height'] / 2 + random.randint(-5, 5)
                                )
                                page.wait_for_timeout(random.randint(80, 300))
                        except:
                            pass
                        text_lower = text.lower()
                        is_nav = 'sign in' in text_lower or 'login' in text_lower
                        
                        if is_nav:
                            try:
                                with page.expect_navigation(timeout=10000):
                                    locator.click(timeout=5000)
                                page.wait_for_load_state('networkidle', timeout=10000)
                                page.wait_for_timeout(3000)
                                log.info(f"✅ click — {clean_selector} (navigation)")
                            except:
                                locator.click(timeout=5000)
                                page.wait_for_timeout(2000)
                                log.info(f"✅ click — {clean_selector}")
                        else:
                            locator.click(timeout=5000)
                            page.wait_for_timeout(1500)
                            log.info(f"✅ click — {clean_selector}")
                
                elif action_type == 'fill':
                    value = action.get('value', '')
                    print(f"  Value: {value}")
                    locator = page.locator(selector)
                    
                    if not locator.is_visible(timeout=3000):
                        status = 'fail'
                        error = 'Element not visible'
                    else:
                        # Human-like: type character by character instead of fill
                        locator.click(timeout=5000)
                        page.wait_for_timeout(random.randint(100, 300))
                        locator.type(value, delay=random.randint(50, 150))
                        
                        if 'password' in selector.lower():
                            page.wait_for_timeout(1000)
                            try:
                                submit_btn = page.locator('button:has-text("Sign In"), button[type="submit"]').first
                                if submit_btn.is_visible(timeout=2000):
                                    print(f"  Auto-submitting after password fill")
                                    try:
                                        with page.expect_navigation(timeout=10000):
                                            submit_btn.click(timeout=5000)
                                        page.wait_for_load_state('networkidle', timeout=10000)
                                        page.wait_for_timeout(3000)
                                        print(f"  Navigated to: {page.url}")
                                        log.info(f"✅ auto-submit after password fill")
                                    except Exception as nav_error:
                                        print(f"  Navigation failed: {str(nav_error)}")
                            except Exception as e:
                                print(f"  Submit button not found: {str(e)}")
                        else:
                            page.wait_for_timeout(500)
                        
                        log.info(f"✅ fill — {selector} = {value}")
                
                elif action_type == 'submit':
                    locator = page.locator(selector)
                    
                    if not locator.is_visible(timeout=3000):
                        status = 'fail'
                        error = 'Element not visible'
                    else:
                        try:
                            with page.expect_navigation(timeout=10000):
                                locator.click(timeout=5000)
                            page.wait_for_load_state('networkidle', timeout=10000)
                            log.info(f"✅ submit — {selector} (navigation completed)")
                        except:
                            locator.click(timeout=5000)
                            page.wait_for_timeout(2000)
                            log.info(f"✅ submit — {selector} (no navigation)")
                
                else:
                    status = 'skip'
                    error = f'Unknown action: {action_type}'
                
                print(f"  Status: {status.upper()}")
                
                step_results.append({
                    'step': {
                        'action': action_type,
                        'selector': selector,
                        'value': action.get('value'),
                        'url': action.get('url')
                    },
                    'status': status,
                    'error': error
                })
            
            except Exception as e:
                print(f"  ERROR: {str(e)}")
                log.error(f"❌ {action_type} failed: {str(e)}")
                step_results.append({
                    'step': {'action': action_type, 'selector': selector},
                    'status': 'fail',
                    'error': str(e)
                })
        
        print("\n"+"="*70)
        print("🔒 RUNNING SECURITY CHECKS")
        print("="*70)
        
        try:
            print("\n  Checking security headers...")
            header_findings = headers.check(page)
            security_findings.extend(header_findings)
            print(f"  Found {len(header_findings)} header issues")
        except Exception as e:
            print(f"  ⚠️  Header check failed: {e}")
        
        try:
            print("\n  Testing for XSS vulnerabilities...")
            xss_findings = xss.check(page)
            security_findings.extend(xss_findings)
            print(f"  Found {len(xss_findings)} XSS issues")
        except Exception as e:
            print(f"  ⚠️  XSS check failed: {e}")
        
        try:
            print("\n  Testing for SQL injection...")
            sqli_findings = sqli.check(page)
            security_findings.extend(sqli_findings)
            print(f"  Found {len(sqli_findings)} SQLi issues")
        except Exception as e:
            print(f"  ⚠️  SQLi check failed: {e}")

        print("\n  Running advanced security checks...")
        try:
            adv_findings = advanced_security.run_all(page)
            security_findings.extend(adv_findings)
            print(f"  Found {len(adv_findings)} advanced security issues")
        except Exception as e:
            print(f"  ⚠️  Advanced security checks failed: {e}")

        print("\n"+"="*70)
        print("🧪 RUNNING QA CHECKS")
        print("="*70)
        qa_findings = []
        try:
            qa_findings = qa_checks.run_all(page)
            print(f"  Found {len(qa_findings)} QA issues")
        except Exception as e:
            print(f"  ⚠️  QA checks failed: {e}")
        
        passed = sum(1 for r in step_results if r['status'] == 'pass')
        failed = sum(1 for r in step_results if r['status'] == 'fail')
        
        print("\n"+"="*70)
        print("🤖 GENERATING AI TEST CASES FOR FIXES")
        print("="*70)
        
        ai_testcases = []
        if GROQ_API_KEY and len(security_findings) > 0:
            try:
                print(f"\n  Generating test cases for {len(security_findings)} security issues...")
                feature_type = recording.get('workflowName', 'workflow')
                ai_testcases = generate_security_testcases(
                    url=base_url,
                    feature=feature_type,
                    count=min(5, max(3, len(security_findings)))
                )
                print(f"  Generated {len(ai_testcases)} AI test cases")
            except Exception as e:
                print(f"  ⚠️  AI test generation failed: {e}")
        elif not GROQ_API_KEY:
            print("\n  ⚠️  Groq API key not configured. Skipping AI test generation.")
        else:
            print("\n  ℹ️  No security issues found. Skipping AI test generation.")
        
        print("\n"+"="*70)
        print("📊 EXECUTION SUMMARY")
        print("="*70)
        print(f"Total Actions: {len(step_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Security Issues: {len(security_findings)}")
        print(f"AI Test Cases: {len(ai_testcases)}")
        print(f"QA Issues: {len(qa_findings)}")
        
        if len(step_results) > 0:
            success_rate = (passed / len(step_results)) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        print("\n"+"="*70)
        print("📝 GENERATING REPORTS")
        print("="*70)
        
        report_data = {
            'template': recording.get('workflowName', 'Chrome Recording'),
            'url': base_url,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'intent': {'type': 'chrome_recording', 'confidence': 'high'},
            'steps': step_results,
            'validations': [],
            'security': {
                'critical': [f for f in security_findings if f.get('severity') == 'critical'],
                'high': [f for f in security_findings if f.get('severity') == 'high'],
                'medium': [f for f in security_findings if f.get('severity') == 'medium'],
                'low': [f for f in security_findings if f.get('severity') == 'low']
            },
            'security_testcases': ai_testcases,
            'qa_findings': qa_findings,
            'elements': [],
            'summary': {
                'total': len(step_results),
                'passed': passed,
                'failed': failed,
                'security_issues': len(security_findings)
            }
        }
        
        output_dir = Path(__file__).parent / "reports"
        output_dir.mkdir(exist_ok=True)
        
        json_path = output_dir / f"{Path(recording_file).stem}_results.json"
        json_path.write_text(json.dumps(report_data, indent=2))
        print(f"\n  JSON Report: {json_path}")
        
        html_path = html_reporter.generate([report_data], [])
        print(f"  HTML Report: {html_path}")

        # GRC Report
        print("\n  Generating GRC Report...")
        try:
            all_findings_for_grc = security_findings + qa_findings
            grc = generate_grc_report(all_findings_for_grc, recording.get('workflowName', 'Workflow'), base_url)
            grc_path = save_grc_report(grc, recording.get('workflowName', 'workflow'))
            print(f"  GRC Report: {grc_path}")
            print(f"  Risk Level: {grc['risk_level']} | Score: {grc['risk_score']}/100")
        except Exception as e:
            print(f"  ⚠️  GRC report failed: {e}")
            grc_path = None
        
        if GROQ_API_KEY:
            print_summary()
            save_session()
        
        if callback_url:
            try:
                print("\n" + "="*70)
                print("📤 SENDING REPORT TO API")
                print("="*70)
                print(f"\n  Callback URL: {callback_url}")

                report_html_content = ''
                if html_path and Path(html_path).exists():
                    report_html_content = Path(html_path).read_text(encoding='utf-8')

                payload = {
                    'workflow_id': workflow_id,
                    'status': 'completed' if failed == 0 else 'failed',
                    'report': report_data,
                    'report_html': report_html_content
                }
                
                response = requests.post(
                    callback_url,
                    json=payload,
                    timeout=30,
                    headers={'Content-Type': 'application/json'}
                )
                
                print(f"\n  Response Status: {response.status_code}")
                if response.status_code == 200:
                    print("  ✅ Report sent successfully!")
                else:
                    print(f"  ⚠️  API returned: {response.text[:200]}")
                    
            except Exception as e:
                print(f"\n  ❌ Failed to send report to API: {str(e)}")
                print("     Report saved locally, continuing...")
        
        print("\n" + "="*70)
        print("✅ TESTING COMPLETE!")
        print("="*70)
        print(f"\n  Open report: open {html_path}")
        
        if len(ai_testcases) > 0:
            print(f"\n  💡 {len(ai_testcases)} AI-generated test cases included in report")
        
        return failed == 0
    
    finally:
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python chrome_recording_runner.py <recording.json> [callback_url]")
        print("\nExample:")
        print("  python chrome_recording_runner.py workflow.json")
        print("  python chrome_recording_runner.py workflow.json https://api.example.com/callback")
        sys.exit(1)
    
    recording_file = sys.argv[1]
    callback_url = sys.argv[2] if len(sys.argv) > 2 else os.getenv('CALLBACK_URL')
    
    if not Path(recording_file).exists():
        print(f"Error: File not found: {recording_file}")
        sys.exit(1)
    
    execute_chrome_recording(recording_file, callback_url)
    sys.exit(0)
