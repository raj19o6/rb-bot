from config.settings import SCREENSHOTS
from core.logger import log
from pathlib import Path

ARTIFACTS = Path(__file__).parent.parent / "reports" / "artifacts"


def run(page, steps: list, variables: dict) -> list[dict]:
    results = []
    for i, step in enumerate(steps):
        action = step["action"]
        try:
            if action == "goto":
                page.goto(step["url"], wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=5000)
            elif action == "fill":
                locator = page.locator(step["selector"])
                # Check if element is visible
                if not locator.is_visible(timeout=2000):
                    raise Exception("Element not visible")
                locator.fill(step["value"], timeout=5000)
            elif action == "click":
                # Check if this is a submit button or login button that will cause navigation
                selector = step["selector"]
                is_submit = "submit" in selector.lower() or "button" in selector.lower()
                
                locator = page.locator(selector)
                # Check if element is visible
                if not locator.is_visible(timeout=2000):
                    raise Exception("Element not visible")
                
                if is_submit:
                    # Wait for navigation after clicking submit buttons
                    try:
                        with page.expect_navigation(timeout=10000):
                            locator.click(timeout=5000)
                        # Wait for page to be fully loaded
                        page.wait_for_load_state("networkidle", timeout=10000)
                        log.info(f"✅ {action} — {selector} (navigation completed)")
                    except:
                        # If no navigation happens, just click normally
                        locator.click(timeout=5000)
                        page.wait_for_timeout(2000)
                        log.info(f"✅ {action} — {selector} (no navigation)")
                else:
                    locator.click(timeout=5000)
                    
            elif action == "press":
                # Pressing Enter on password field usually triggers form submit
                locator = page.locator(step["selector"])
                # Check if element is visible
                if not locator.is_visible(timeout=2000):
                    raise Exception("Element not visible")
                    
                try:
                    with page.expect_navigation(timeout=10000):
                        locator.press(step["key"], timeout=5000)
                    # Wait for page to be fully loaded
                    page.wait_for_load_state("networkidle", timeout=10000)
                    log.info(f"✅ {action} — {step['key']} (navigation completed)")
                except:
                    # If no navigation, just press the key
                    locator.press(step["key"], timeout=5000)
                    page.wait_for_timeout(2000)
                    log.info(f"✅ {action} — {step['key']} (no navigation)")
                    
            elif action == "select_first":
                opts = page.locator(step["selector"]).locator("option").all()
                if opts:
                    page.locator(step["selector"]).select_option(index=0)
            elif action == "wait":
                page.wait_for_timeout(step.get("ms", 1000))

            if action not in ["click", "press"]:
                log.info(f"✅ {action} — {step.get('selector', step.get('url', ''))}")
            results.append({"step": step, "status": "pass"})

        except Exception as e:
            log.error(f"❌ {action} failed: {e}")
            if SCREENSHOTS:
                shot = ARTIFACTS / f"fail_{action}_{i}.png"
                page.screenshot(path=str(shot))
            results.append({"step": step, "status": "fail", "error": str(e)})

    return results
