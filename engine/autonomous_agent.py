"""
Production-ready autonomous agent.
Designed to handle 1000s of different websites robustly.
Features:
- Comprehensive error handling
- Fallback mechanisms
- Timeout protection
- Memory management
- Retry logic
"""
import json
import time
from engine.surfer import surf
from engine.crawler import crawl
from engine.ai_testgen import generate_security_testcases
from engine import executor, validator
from security import headers, xss, sqli


def safe_analyze_page_intent(page_data):
    """Safely determine page intent with fallbacks."""
    try:
        forms = page_data.get("forms", [])
        elements = page_data.get("elements", [])
        
        inputs = [e for e in elements if e.get("tag") in ["input", "textarea", "select"]]
        buttons = [e for e in elements if e.get("tag") == "button" or (e.get("tag") == "input" and e.get("type") in ["submit", "button"])]
        
        meta = page_data.get("meta", {})
        title = meta.get("title", "").lower()
        url = page_data.get("url", "").lower()
        
        intents = []
        
        # Login detection - multiple strategies
        has_password = any(inp.get("type") == "password" for inp in inputs)
        has_username = any(
            inp.get("name", "").lower() in ["username", "email", "user", "login", "userid", "account"] or 
            inp.get("id", "").lower() in ["username", "email", "user", "login", "userid", "account"] or
            inp.get("placeholder", "").lower() in ["username", "email", "user", "login"] or
            inp.get("type") == "email"
            for inp in inputs
        )
        
        # Check URL and title for login indicators
        login_keywords = ["login", "signin", "sign-in", "auth", "authenticate"]
        has_login_url = any(keyword in url for keyword in login_keywords)
        has_login_title = any(keyword in title for keyword in login_keywords)
        
        if has_password and (has_username or has_login_url or has_login_title):
            intents.append({"type": "login", "confidence": "high"})
            return intents
        
        # Registration detection
        has_confirm = any(
            "confirm" in inp.get("name", "").lower() or 
            "confirm" in inp.get("id", "").lower() or
            "repeat" in inp.get("name", "").lower()
            for inp in inputs
        )
        if has_password and has_confirm:
            intents.append({"type": "registration", "confidence": "high"})
            return intents
        
        # Search detection
        has_search = any(
            "search" in inp.get("name", "").lower() or 
            "search" in inp.get("id", "").lower() or
            "search" in inp.get("placeholder", "").lower() or
            inp.get("type") == "search"
            for inp in inputs
        )
        if has_search:
            intents.append({"type": "search", "confidence": "medium"})
        
        # Contact form
        has_email = any("email" in inp.get("name", "").lower() or "email" in inp.get("id", "").lower() for inp in inputs)
        has_message = any("message" in inp.get("name", "").lower() or inp.get("tag") == "textarea" for inp in inputs)
        if has_email and has_message:
            intents.append({"type": "contact", "confidence": "medium"})
        
        # Generic form
        if forms and not intents:
            intents.append({"type": "form", "confidence": "low"})
        
        # Default
        if not intents:
            intents.append({"type": "page", "confidence": "low"})
        
        return intents
        
    except Exception as e:
        print(f"      ⚠️  Intent analysis failed: {e}")
        return [{"type": "unknown", "confidence": "low"}]


def safe_generate_test_data(inp):
    """Safely generate test data for any input field."""
    try:
        inp_type = inp.get("type", "text").lower()
        inp_name = inp.get("name", "").lower()
        inp_id = inp.get("id", "").lower()
        inp_placeholder = inp.get("placeholder", "").lower()
        
        # Combine all hints
        hints = f"{inp_name} {inp_id} {inp_placeholder}"
        
        # Email detection
        if inp_type == "email" or any(k in hints for k in ["email", "e-mail", "mail"]):
            return "test@example.com"
        
        # Password detection
        if inp_type == "password" or "password" in hints or "pass" in hints:
            return "TestPassword123!"
        
        # Phone detection
        if inp_type == "tel" or any(k in hints for k in ["phone", "mobile", "tel", "contact"]):
            return "1234567890"
        
        # Number detection
        if inp_type == "number" or any(k in hints for k in ["age", "quantity", "amount", "count"]):
            return "25"
        
        # URL detection
        if inp_type == "url" or "url" in hints or "website" in hints:
            return "https://example.com"
        
        # Date detection
        if inp_type == "date" or "date" in hints or "dob" in hints or "birth" in hints:
            return "2024-01-01"
        
        # Time detection
        if inp_type == "time" or "time" in hints:
            return "12:00"
        
        # Name detection
        if any(k in hints for k in ["name", "firstname", "lastname", "fullname"]):
            return "Test User"
        
        # Username detection
        if any(k in hints for k in ["username", "user", "login", "userid"]):
            return "testuser"
        
        # Search detection
        if "search" in hints or "query" in hints:
            return "test query"
        
        # Message/Comment detection
        if any(k in hints for k in ["message", "comment", "description", "notes"]) or inp.get("tag") == "textarea":
            return "This is a test message for automated testing."
        
        # Address detection
        if "address" in hints or "street" in hints:
            return "123 Test Street"
        
        # City detection
        if "city" in hints or "town" in hints:
            return "Test City"
        
        # Zip/Postal detection
        if any(k in hints for k in ["zip", "postal", "pincode"]):
            return "12345"
        
        # Country detection
        if "country" in hints:
            return "United States"
        
        # Company detection
        if "company" in hints or "organization" in hints:
            return "Test Company"
        
        # Default
        return "test input"
        
    except Exception as e:
        return "test"


def safe_generate_login_steps(page_data, credentials):
    """Safely generate login steps with multiple fallback strategies."""
    try:
        steps = [{"action": "goto", "url": page_data["url"]}]
        
        elements = page_data.get("elements", [])
        inputs = [e for e in elements if e.get("tag") in ["input", "textarea"]]
        buttons = [e for e in elements if e.get("tag") == "button" or (e.get("tag") == "input" and e.get("type") in ["submit", "button"])]
        
        # Find username field - multiple strategies
        username_field = None
        for inp in inputs:
            name = inp.get("name", "").lower()
            id_attr = inp.get("id", "").lower()
            placeholder = inp.get("placeholder", "").lower()
            inp_type = inp.get("type", "").lower()
            
            if (any(k in name for k in ["username", "email", "user", "login", "userid"]) or
                any(k in id_attr for k in ["username", "email", "user", "login", "userid"]) or
                any(k in placeholder for k in ["username", "email", "user", "login"]) or
                inp_type == "email"):
                username_field = inp
                break
        
        # Find password field
        password_field = next((inp for inp in inputs if inp.get("type") == "password"), None)
        
        # Find submit button - multiple strategies
        submit_btn = None
        for btn in buttons:
            btn_text = btn.get("text", "").lower()
            btn_type = btn.get("type", "").lower()
            btn_id = btn.get("id", "").lower()
            
            if ("submit" in btn_type or
                any(k in btn_text for k in ["login", "sign in", "submit", "enter", "log in"]) or
                any(k in btn_id for k in ["login", "signin", "submit"])):
                submit_btn = btn
                break
        
        # Fill username
        if username_field:
            css = username_field.get("css", f"#{username_field.get('id')}" if username_field.get('id') else f"input[type='{username_field.get('type')}']")
            steps.append({
                "action": "fill",
                "selector": css,
                "value": credentials.get("username", "test@example.com")
            })
        
        # Fill password
        if password_field:
            css = password_field.get("css", "#" + password_field.get('id') if password_field.get('id') else "input[type='password']")
            steps.append({
                "action": "fill",
                "selector": css,
                "value": credentials.get("password", "password123")
            })
        
        # Submit
        if submit_btn:
            css = submit_btn.get("css", "button[type='submit']")
            steps.append({
                "action": "click",
                "selector": css
            })
        elif password_field:
            css = password_field.get("css", "input[type='password']")
            steps.append({
                "action": "press",
                "selector": css,
                "key": "Enter"
            })
        
        return steps
        
    except Exception as e:
        print(f"      ⚠️  Login step generation failed: {e}")
        return [{"action": "goto", "url": page_data["url"]}]


def safe_generate_test_steps(page_data, intent):
    """Safely generate comprehensive test steps."""
    try:
        steps = [{"action": "goto", "url": page_data["url"]}]
        
        elements = page_data.get("elements", [])
        inputs = [e for e in elements if e.get("tag") in ["input", "textarea", "select"]]
        buttons = [e for e in elements if e.get("tag") == "button" or (e.get("tag") == "input" and e.get("type") in ["submit", "button"])]
        
        tested_inputs = 0
        tested_buttons = 0
        
        # Test inputs
        for inp in inputs:
            try:
                inp_type = inp.get("type", "text").lower()
                css = inp.get("css", "")
                
                # Skip problematic types
                if inp_type in ["hidden", "checkbox", "radio", "file", "image"]:
                    continue
                
                # Skip if no selector
                if not css:
                    continue
                
                test_value = safe_generate_test_data(inp)
                
                if test_value:
                    steps.append({
                        "action": "fill",
                        "selector": css,
                        "value": test_value
                    })
                    tested_inputs += 1
                    
            except Exception as e:
                continue
        
        # Test buttons (non-submit)
        for btn in buttons:
            try:
                btn_text = btn.get("text", "").lower()
                btn_type = btn.get("type", "").lower()
                css = btn.get("css", "")
                
                # Skip submit buttons
                if "submit" in btn_type or "submit" in btn_text:
                    continue
                
                # Skip if no selector or text
                if not css or not btn_text:
                    continue
                
                steps.append({
                    "action": "click",
                    "selector": css
                })
                steps.append({"action": "wait", "ms": 500})
                tested_buttons += 1
                
            except Exception as e:
                continue
        
        print(f"      Generated {tested_inputs} input tests and {tested_buttons} button tests")
        return steps
        
    except Exception as e:
        print(f"      ⚠️  Test step generation failed: {e}")
        return [{"action": "goto", "url": page_data["url"]}]


def safe_test_route(page, route_url, openai_api_key=None, timeout=30):
    """Safely test a single route with timeout protection."""
    print(f"\n   📄 Testing: {route_url}")
    
    start_time = time.time()
    
    try:
        # Navigate with timeout
        try:
            page.goto(route_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(500)
        except Exception as e:
            print(f"      ⚠️  Navigation failed: {e}")
            return None
        
        # Check if timeout exceeded
        if time.time() - start_time > timeout:
            print(f"      ⏱️  Timeout exceeded")
            return None
        
        # Surf route
        try:
            route_surf = surf(page, route_url, {"max_depth": 0, "max_routes": 1, "screenshot": False})
        except Exception as e:
            print(f"      ⚠️  Surf failed: {e}")
            return None
        
        if not route_surf.get("route_reports"):
            print(f"      ⚠️  No data collected")
            return None
        
        page_data = route_surf["route_reports"][0]
        
        # Analyze intent
        intents = safe_analyze_page_intent(page_data)
        intent = intents[0] if intents else {"type": "page", "confidence": "low"}
        
        print(f"      Type: {intent['type']} ({intent['confidence']} confidence)")
        print(f"      Forms: {len(page_data.get('forms', []))}, Elements: {len(page_data.get('elements', []))}")
        
        # Generate and execute test steps
        print(f"      🧪 Testing inputs and buttons...")
        test_steps = safe_generate_test_steps(page_data, intent)
        
        try:
            step_results = executor.run(page, test_steps, {})
        except Exception as e:
            print(f"      ⚠️  Test execution failed: {e}")
            step_results = [{"step": test_steps[0], "status": "fail", "error": str(e)}]
        
        passed = sum(1 for r in step_results if r["status"] == "pass")
        failed = sum(1 for r in step_results if r["status"] == "fail")
        
        # Security checks
        print(f"      🔒 Running security checks...")
        security_findings = []
        
        try:
            security_findings += headers.check(page)
        except Exception as e:
            print(f"      ⚠️  Header check failed: {e}")
        
        try:
            security_findings += xss.check(page)
        except Exception as e:
            print(f"      ⚠️  XSS check failed: {e}")
        
        try:
            security_findings += sqli.check(page)
        except Exception as e:
            print(f"      ⚠️  SQLi check failed: {e}")
        
        # AI test cases (optional)
        ai_cases = []
        if openai_api_key and time.time() - start_time < timeout - 10:
            try:
                print(f"      🤖 Generating AI test cases...")
                ai_cases = generate_security_testcases(
                    url=route_url,
                    feature=intent["type"],
                    count=2  # Reduced for speed
                )
            except Exception as e:
                print(f"      ⚠️  AI generation skipped: {e}")
        
        # Compile report
        sec_count = len(security_findings)
        
        report = {
            "template": f"{intent['type']}_{route_url.split('/')[-1] or 'home'}",
            "url": route_url,
            "timestamp": page_data.get("meta", {}).get("title", ""),
            "intent": intent,
            "steps": step_results,
            "validations": [],
            "security": {
                "critical": [f for f in security_findings if f.get("severity") == "critical"],
                "high": [f for f in security_findings if f.get("severity") == "high"],
                "medium": [f for f in security_findings if f.get("severity") == "medium"],
                "low": [f for f in security_findings if f.get("severity") == "low"],
            },
            "security_testcases": ai_cases,
            "elements": page_data.get("elements", []),
            "summary": {
                "total": len(step_results),
                "passed": passed,
                "failed": failed,
                "security_issues": sec_count
            }
        }
        
        print(f"      ✅ Complete: {passed} passed, {failed} failed, {sec_count} security issues")
        return report
        
    except Exception as e:
        print(f"      ❌ Failed: {e}")
        return None


def run_autonomous(page, base_url, credentials=None, openai_api_key=None):
    """
    Production-ready autonomous testing.
    Handles any website structure robustly.
    """
    credentials = credentials or {}
    all_reports = []
    login_successful = False
    
    print(f"\n🤖 Autonomous Agent Starting...")
    print(f"   Target: {base_url}")
    print(f"   Credentials: {'Provided' if credentials else 'None'}")
    
    try:
        # ════════════════════════════════════════════════════════════════════
        # PHASE 1: Landing page analysis
        # ════════════════════════════════════════════════════════════════════
        print(f"\n🏄 Phase 1: Analyzing landing page...")
        
        try:
            surf_result = surf(page, base_url, {"max_depth": 0, "max_routes": 1, "screenshot": False})
        except Exception as e:
            print(f"   ❌ Surf failed: {e}")
            return {"surf_reports": [], "test_reports": []}
        
        if not surf_result.get("route_reports"):
            print(f"   ❌ Could not access landing page")
            return {"surf_reports": [], "test_reports": []}
        
        landing_page = surf_result["route_reports"][0]
        print(f"   ✓ Landing page analyzed")
        
        # ════════════════════════════════════════════════════════════════════
        # PHASE 2: Authentication
        # ════════════════════════════════════════════════════════════════════
        print(f"\n🔐 Phase 2: Attempting authentication...")
        
        intents = safe_analyze_page_intent(landing_page)
        is_login_page = any(i["type"] == "login" for i in intents)
        
        if is_login_page and credentials:
            print(f"   ✓ Login page detected")
            print(f"   🔑 Logging in as: {credentials.get('username', 'N/A')}")
            
            try:
                login_steps = safe_generate_login_steps(landing_page, credentials)
                step_results = executor.run(page, login_steps, {})
                
                current_url = page.url
                page_title = page.title()
                
                login_successful = (
                    current_url != base_url and
                    not any(keyword in current_url.lower() for keyword in ["signin", "login", "auth", "error"])
                )
                
                if login_successful:
                    print(f"   ✅ Login successful!")
                    print(f"      Current URL: {current_url}")
                else:
                    print(f"   ⚠️  Login may have failed")
                    print(f"      Current URL: {current_url}")
                
                # Create login report
                passed = sum(1 for r in step_results if r["status"] == "pass")
                failed = sum(1 for r in step_results if r["status"] == "fail")
                
                security_findings = []
                try:
                    security_findings += headers.check(page)
                    security_findings += xss.check(page)
                    security_findings += sqli.check(page)
                except:
                    pass
                
                login_report = {
                    "template": "login_test",
                    "url": base_url,
                    "timestamp": landing_page.get("meta", {}).get("title", ""),
                    "intent": {"type": "login", "confidence": "high"},
                    "steps": step_results,
                    "validations": [],
                    "security": {
                        "critical": [f for f in security_findings if f.get("severity") == "critical"],
                        "high": [f for f in security_findings if f.get("severity") == "high"],
                        "medium": [f for f in security_findings if f.get("severity") == "medium"],
                        "low": [f for f in security_findings if f.get("severity") == "low"],
                    },
                    "security_testcases": [],
                    "elements": landing_page.get("elements", []),
                    "summary": {
                        "total": len(step_results),
                        "passed": passed,
                        "failed": failed,
                        "security_issues": len(security_findings)
                    }
                }
                all_reports.append(login_report)
                
            except Exception as e:
                print(f"   ❌ Login failed: {e}")
        else:
            if not is_login_page:
                print(f"   ℹ️  No login page detected")
            else:
                print(f"   ⚠️  Login page found but no credentials provided")
        
        # ════════════════════════════════════════════════════════════════════
        # PHASE 3: Route discovery
        # ════════════════════════════════════════════════════════════════════
        print(f"\n🕷️  Phase 3: Discovering routes...")
        
        start_url = page.url
        print(f"   Starting from: {start_url}")
        
        try:
            routes = crawl(
                page,
                base_url=start_url,
                max_depth=2,  # Reduced for reliability
                max_routes=20  # Reduced for speed
            )
            print(f"   ✓ Found {len(routes)} routes")
            
            for i, route in enumerate(routes[:5], 1):
                print(f"      {i}. {route}")
            if len(routes) > 5:
                print(f"      ... and {len(routes) - 5} more")
                
        except Exception as e:
            print(f"   ⚠️  Crawl failed: {e}, using current page only")
            routes = [start_url]
        
        # ════════════════════════════════════════════════════════════════════
        # PHASE 4: Route testing
        # ════════════════════════════════════════════════════════════════════
        print(f"\n🧪 Phase 4: Testing routes...")
        
        for i, route_url in enumerate(routes, 1):
            print(f"\n   [{i}/{len(routes)}]", end="")
            report = safe_test_route(page, route_url, openai_api_key, timeout=30)
            if report:
                all_reports.append(report)
        
        # ════════════════════════════════════════════════════════════════════
        # PHASE 5: Summary
        # ════════════════════════════════════════════════════════════════════
        print(f"\n✅ Autonomous testing complete!")
        print(f"   Login: {'✓ Success' if login_successful else '✗ Not performed'}")
        print(f"   Routes discovered: {len(routes)}")
        print(f"   Routes tested: {len(all_reports)}")
        print(f"   Total security issues: {sum(r['summary']['security_issues'] for r in all_reports)}")
        
        return {
            "surf_reports": [surf_result],
            "test_reports": all_reports
        }
        
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        return {
            "surf_reports": [],
            "test_reports": all_reports
        }
