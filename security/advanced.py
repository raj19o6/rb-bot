import re
import time
from core.logger import log
from utils.selectors import get_input_selectors

# ── CSRF ─────────────────────────────────────────────────────────
def check_csrf(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        forms = page.query_selector_all('form')
        for form in forms:
            inputs = form.query_selector_all('input[type="hidden"]')
            values = [i.get_attribute('name') or '' for i in inputs]
            has_token = any(
                any(k in v.lower() for k in ['csrf', 'token', '_token', 'xsrf', 'nonce'])
                for v in values
            )
            if not has_token:
                action = form.get_attribute('action') or url
                log.warning(f'⚠️  No CSRF token in form: {action}')
                findings.append({
                    'type': 'missing_csrf_token',
                    'form_action': action,
                    'reason': 'Form has no CSRF token — vulnerable to cross-site request forgery',
                    'severity': 'high',
                    'url': url,
                    'owasp': 'A01:2021 – Broken Access Control',
                    'iso27001': 'A.14.2.5',
                    'cvss': 8.1,
                })
    except Exception as e:
        log.warning(f'CSRF check failed: {e}')
    return findings


# ── Open Redirect ────────────────────────────────────────────────
REDIRECT_PAYLOADS = [
    'https://evil.com',
    '//evil.com',
    '/\\evil.com',
]

def check_open_redirect(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse, urljoin
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        redirect_params = [k for k in params if any(r in k.lower() for r in ['redirect', 'return', 'next', 'url', 'goto', 'dest'])]

        for param in redirect_params:
            for payload in REDIRECT_PAYLOADS:
                try:
                    new_params = dict(params)
                    new_params[param] = [payload]
                    new_query = '&'.join(f'{k}={v[0]}' for k, v in new_params.items())
                    test_url = urlunparse(parsed._replace(query=new_query))
                    page.goto(test_url, wait_until='domcontentloaded', timeout=8000)
                    current = page.url
                    if 'evil.com' in current:
                        findings.append({
                            'type': 'open_redirect',
                            'param': param,
                            'payload': payload,
                            'severity': 'high',
                            'url': url,
                            'owasp': 'A01:2021 – Broken Access Control',
                            'iso27001': 'A.14.2.5',
                            'cvss': 6.1,
                        })
                        break
                except Exception:
                    continue
    except Exception as e:
        log.warning(f'Open redirect check failed: {e}')
    return findings


# ── Session Cookie Security ──────────────────────────────────────
def check_cookies(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        cookies = page.context.cookies()
        session_keywords = ['session', 'sess', 'auth', 'token', 'jwt', 'sid', 'user']
        for cookie in cookies:
            name = cookie.get('name', '').lower()
            is_session = any(k in name for k in session_keywords)
            if not is_session:
                continue
            if not cookie.get('httpOnly'):
                findings.append({
                    'type': 'cookie_missing_httponly',
                    'cookie': cookie['name'],
                    'reason': 'Session cookie missing HttpOnly flag — accessible via JavaScript',
                    'severity': 'high',
                    'url': url,
                    'owasp': 'A02:2021 – Cryptographic Failures',
                    'iso27001': 'A.14.1.3',
                    'cvss': 7.5,
                })
            if not cookie.get('secure'):
                findings.append({
                    'type': 'cookie_missing_secure',
                    'cookie': cookie['name'],
                    'reason': 'Session cookie missing Secure flag — sent over HTTP',
                    'severity': 'medium',
                    'url': url,
                    'owasp': 'A02:2021 – Cryptographic Failures',
                    'iso27001': 'A.14.1.3',
                    'cvss': 5.3,
                })
            samesite = cookie.get('sameSite', '').lower()
            if samesite not in ['strict', 'lax']:
                findings.append({
                    'type': 'cookie_weak_samesite',
                    'cookie': cookie['name'],
                    'reason': f'Session cookie SameSite={samesite or "None"} — CSRF risk',
                    'severity': 'medium',
                    'url': url,
                    'owasp': 'A01:2021 – Broken Access Control',
                    'iso27001': 'A.14.2.5',
                    'cvss': 4.3,
                })
    except Exception as e:
        log.warning(f'Cookie check failed: {e}')
    return findings


# ── Sensitive Data Exposure ──────────────────────────────────────
SENSITIVE_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})', 'API Key exposed', 'critical'),
    (r'(?i)(secret[_-]?key|secret)\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})', 'Secret Key exposed', 'critical'),
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{6,})', 'Password exposed in source', 'critical'),
    (r'(?i)(aws_access_key_id|aws_secret)\s*[:=]\s*["\']?([A-Za-z0-9/+=]{20,})', 'AWS credentials exposed', 'critical'),
    (r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', 'Email address exposed', 'low'),
    (r'(?i)bearer\s+[A-Za-z0-9\-_\.]+', 'Bearer token exposed', 'high'),
    (r'(?i)(private[_-]?key|-----BEGIN)', 'Private key exposed', 'critical'),
]

def check_sensitive_data(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        content = page.content()
        for pattern, reason, severity in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                log.warning(f'⚠️  {reason} at {url}')
                findings.append({
                    'type': 'sensitive_data_exposure',
                    'reason': reason,
                    'severity': severity,
                    'url': url,
                    'owasp': 'A02:2021 – Cryptographic Failures',
                    'iso27001': 'A.8.2.3',
                    'cvss': 9.1 if severity == 'critical' else 7.5 if severity == 'high' else 3.1,
                })
    except Exception as e:
        log.warning(f'Sensitive data check failed: {e}')
    return findings


# ── Rate Limiting ────────────────────────────────────────────────
def check_rate_limiting(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        selectors = get_input_selectors(page)
        password_sel = next((s for s in selectors if 'password' in s.lower()), None)
        username_sel = next((s for s in selectors if any(k in s.lower() for k in ['email', 'username', 'user'])), None)

        if not (password_sel and username_sel):
            return findings

        blocked = False
        for attempt in range(6):
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=8000)
                page.locator(username_sel).fill('test@test.com', timeout=3000)
                page.locator(password_sel).fill(f'wrongpassword{attempt}', timeout=3000)
                page.keyboard.press('Enter')
                page.wait_for_timeout(800)
                content = page.content().lower()
                if any(k in content for k in ['too many', 'rate limit', 'blocked', 'captcha', 'locked', 'try again later']):
                    blocked = True
                    break
            except Exception:
                continue

        if not blocked:
            findings.append({
                'type': 'no_rate_limiting',
                'reason': 'Login form allows unlimited attempts — brute force possible',
                'severity': 'high',
                'url': url,
                'owasp': 'A07:2021 – Identification and Authentication Failures',
                'iso27001': 'A.9.4.2',
                'cvss': 7.5,
            })
    except Exception as e:
        log.warning(f'Rate limit check failed: {e}')
    return findings


# ── Blind SQLi (time-based) ──────────────────────────────────────
BLIND_SQLI_PAYLOADS = [
    ("'; WAITFOR DELAY '0:0:4'--", 4),
    ("' OR SLEEP(4)--", 4),
    ("1; SELECT pg_sleep(4)--", 4),
]

def check_blind_sqli(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        selectors = get_input_selectors(page)
        for selector in selectors[:3]:  # limit to first 3 fields
            for payload, delay in BLIND_SQLI_PAYLOADS:
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=8000)
                    locator = page.locator(selector)
                    if not locator.is_visible(timeout=2000):
                        continue
                    locator.fill(payload, timeout=3000)
                    start = time.time()
                    page.keyboard.press('Enter')
                    page.wait_for_timeout(5000)
                    elapsed = time.time() - start
                    if elapsed >= delay:
                        findings.append({
                            'type': 'blind_sql_injection',
                            'selector': selector,
                            'payload': payload,
                            'elapsed': round(elapsed, 2),
                            'severity': 'critical',
                            'url': url,
                            'owasp': 'A03:2021 – Injection',
                            'iso27001': 'A.14.2.5',
                            'cvss': 9.8,
                        })
                        break
                except Exception:
                    continue
    except Exception as e:
        log.warning(f'Blind SQLi check failed: {e}')
    return findings


# ── DOM XSS ──────────────────────────────────────────────────────
DOM_XSS_PAYLOADS = [
    '<img src=x onerror=window.__xss_hit=1>',
    '<svg onload=window.__xss_hit=1>',
]

def check_dom_xss(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        selectors = get_input_selectors(page)
        for selector in selectors:
            for payload in DOM_XSS_PAYLOADS:
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=8000)
                    locator = page.locator(selector)
                    if not locator.is_visible(timeout=2000):
                        continue
                    page.evaluate("window.__xss_hit = 0")
                    locator.fill(payload, timeout=3000)
                    page.keyboard.press('Tab')
                    page.wait_for_timeout(1000)
                    hit = page.evaluate("window.__xss_hit")
                    if hit:
                        findings.append({
                            'type': 'dom_xss',
                            'selector': selector,
                            'payload': payload,
                            'severity': 'high',
                            'url': url,
                            'owasp': 'A03:2021 – Injection',
                            'iso27001': 'A.14.2.5',
                            'cvss': 8.8,
                        })
                        break
                except Exception:
                    continue
    except Exception as e:
        log.warning(f'DOM XSS check failed: {e}')
    return findings


# ── Broken Links ─────────────────────────────────────────────────
def check_broken_links(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        hrefs = page.eval_on_selector_all('a[href]', 'els => els.map(e => e.href)')
        from urllib.parse import urlparse
        base = urlparse(url).netloc
        checked = set()
        for href in hrefs[:20]:  # limit to 20
            if href in checked or not href.startswith('http'):
                continue
            if urlparse(href).netloc != base:
                continue
            checked.add(href)
            try:
                resp = page.request.get(href, timeout=5000)
                if resp.status == 404:
                    findings.append({
                        'type': 'broken_link',
                        'href': href,
                        'status': 404,
                        'severity': 'low',
                        'url': url,
                        'reason': 'Page returns 404 Not Found',
                        'owasp': 'A05:2021 – Security Misconfiguration',
                        'iso27001': 'A.12.6.1',
                        'cvss': 2.0,
                    })
            except Exception:
                continue
    except Exception as e:
        log.warning(f'Broken links check failed: {e}')
    return findings


def run_all(page) -> list[dict]:
    """Run all advanced security checks and return combined findings."""
    all_findings = []
    checks = [
        ('CSRF', check_csrf),
        ('Cookies', check_cookies),
        ('Sensitive Data', check_sensitive_data),
        ('DOM XSS', check_dom_xss),
        ('Broken Links', check_broken_links),
        ('Open Redirect', check_open_redirect),
        ('Rate Limiting', check_rate_limiting),
        ('Blind SQLi', check_blind_sqli),
    ]
    for name, fn in checks:
        try:
            print(f'    → {name}...', end=' ', flush=True)
            results = fn(page)
            all_findings.extend(results)
            print(f'{len(results)} issue(s)')
        except Exception as e:
            print(f'skipped ({e})')
    return all_findings
