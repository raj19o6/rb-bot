from utils.selectors import get_input_selectors
from utils.helpers import truncate
from core.logger import log

PAYLOADS = [
    "<script>alert('xss')</script>",
    '"><img src=x onerror=alert(1)>',
    "';alert('xss')//",
    "<svg onload=alert(1)>",
]


def check(page) -> list[dict]:
    """
    Inject XSS payloads into all visible inputs on the current page.
    Returns findings where payload is reflected in the response.
    """
    findings = []
    url = page.url
    selectors = get_input_selectors(page)

    if not selectors:
        log.info("XSS: no input fields found on page")
        return findings

    for selector in selectors:
        for payload in PAYLOADS:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(500)  # Wait for elements to be visible
                
                # Check if element is visible before trying to fill
                locator = page.locator(selector)
                if not locator.is_visible(timeout=2000):
                    continue  # Skip invisible elements
                
                locator.fill(payload, timeout=5000)
                page.keyboard.press("Tab")  # trigger any JS validation

                content = page.content()
                if payload in content:
                    log.warning(f"⚠️  XSS reflected — {selector} — {truncate(payload)}")
                    findings.append({
                        "type": "reflected_xss",
                        "selector": selector,
                        "payload": payload,
                        "severity": "high",
                        "url": url,
                    })
                    break  # one confirmed hit per field is enough

            except Exception as e:
                # Silently skip elements that can't be tested
                continue

    return findings
