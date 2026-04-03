"""
Builds and executes auto-generated test steps from scraped elements.
For each route: fills inputs with test values, clicks buttons, runs security checks.
"""

from engine.scraper import scrape
from engine.executor import run as exec_steps
from engine.validator import run as exec_validations
from reports.report_generator import save
from security import headers, xss, sqli
from core.logger import log


_FILL_VALUES = {
    "email":    "test@example.com",
    "password": "Test@1234",
    "search":   "test",
    "text":     "test input",
    "tel":      "1234567890",
    "number":   "42",
    "url":      "https://example.com",
    "":         "test",
}


def _fill_value(el: dict) -> str:
    el_type = el.get("type", "").lower()
    name    = el.get("name", "").lower()
    ph      = el.get("placeholder", "").lower()
    for hint in (el_type, name, ph):
        for key, val in _FILL_VALUES.items():
            if key and key in hint:
                return val
    return _FILL_VALUES[""]


def run_route(page, url: str, security_checks: list) -> dict:
    """
    Visit a route, scrape elements, build steps, execute, run security checks.
    Returns a full report dict for this route.
    """
    log.info(f"Auto-runner: testing {url}")

    # Navigate
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(300)
    except Exception as e:
        log.error(f"Auto-runner: failed to load {url} — {e}")
        return None

    elements = scrape(page)

    # Build steps from scraped elements
    steps = [{"action": "goto", "url": url}]
    clicked_submit = False

    for el in elements:
        tag     = el["tag"]
        el_type = el["type"].lower()
        css     = el["css"]

        if tag in ("input", "textarea") and el_type not in ("submit", "button", "reset", "checkbox", "radio", "file"):
            steps.append({"action": "fill", "selector": css, "value": _fill_value(el), "xpath": el["xpath"]})

        elif tag == "select":
            steps.append({"action": "select_first", "selector": css, "xpath": el["xpath"]})

        elif (tag == "button" or el_type in ("submit", "button")) and not clicked_submit:
            steps.append({"action": "click", "selector": css, "xpath": el["xpath"]})
            clicked_submit = True  # only click one submit per form to avoid navigation loops

    # Execute steps
    step_results = exec_steps(page, steps, {})

    # Validations — just check page loaded (200-like, no crash)
    validations = [{"type": "text_present", "value": ""}]
    val_results = exec_validations(page, validations)

    # Security checks
    security_findings = []
    if "headers" in security_checks:
        security_findings += headers.check(page)
    if "xss" in security_checks:
        security_findings += xss.check(page)
    if "sqli" in security_checks:
        security_findings += sqli.check(page)

    # Route name from path
    from urllib.parse import urlparse
    path = urlparse(url).path.strip("/") or "home"
    route_name = f"auto_{path.replace('/', '_')}"

    report = save(route_name, step_results, val_results, security_findings)
    report["url"]      = url
    report["elements"] = elements
    return report
