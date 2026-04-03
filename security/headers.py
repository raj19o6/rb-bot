from core.logger import log

REQUIRED_HEADERS = {
    "content-security-policy": "Prevents XSS and data injection attacks",
    "x-frame-options": "Prevents clickjacking",
    "x-content-type-options": "Prevents MIME sniffing",
    "strict-transport-security": "Enforces HTTPS",
    "referrer-policy": "Controls referrer information",
    "permissions-policy": "Controls browser feature access",
}


def check(page) -> list[dict]:
    """
    Navigate to the current page URL and inspect response headers.
    Returns a list of findings (missing or weak headers).
    """
    findings = []
    url = page.url

    # Intercept the response headers via a fresh request
    response = page.request.get(url)
    headers = {k.lower(): v for k, v in response.headers.items()}

    for header, reason in REQUIRED_HEADERS.items():
        if header not in headers:
            log.warning(f"⚠️  Missing header: {header}")
            findings.append({
                "type": "missing_header",
                "header": header,
                "reason": reason,
                "severity": "medium",
                "url": url,
            })
        else:
            log.info(f"✅ Header present: {header}")

    # Extra: warn if CSP is too permissive
    csp = headers.get("content-security-policy", "")
    if "unsafe-inline" in csp or "unsafe-eval" in csp:
        findings.append({
            "type": "weak_csp",
            "header": "content-security-policy",
            "value": csp,
            "reason": "CSP contains unsafe-inline or unsafe-eval",
            "severity": "high",
            "url": url,
        })

    return findings
