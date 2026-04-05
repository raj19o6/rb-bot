"""
QA Testing Module
Covers: negative tests, boundary tests, assertions, console errors,
        performance metrics, accessibility checks, mobile viewport.
"""
import time
from core.logger import log
from utils.selectors import get_input_selectors


# ── Console Error Capture ────────────────────────────────────────
def check_console_errors(page) -> list[dict]:
    findings = []
    errors = []

    def on_console(msg):
        if msg.type in ('error', 'warning'):
            errors.append({'type': msg.type, 'text': msg.text})

    page.on('console', on_console)
    try:
        page.reload(wait_until='networkidle', timeout=15000)
        page.wait_for_timeout(2000)
    except Exception:
        pass
    page.remove_listener('console', on_console)

    for err in errors:
        findings.append({
            'type': 'console_error',
            'message': err['text'][:200],
            'level': err['type'],
            'severity': 'medium' if err['type'] == 'error' else 'low',
            'url': page.url,
            'category': 'QA',
        })
    return findings


# ── Performance Metrics ──────────────────────────────────────────
def check_performance(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        start = time.time()
        page.goto(url, wait_until='networkidle', timeout=30000)
        load_time = round((time.time() - start) * 1000)

        metrics = page.evaluate("""() => {
            const nav = performance.getEntriesByType('navigation')[0];
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            return {
                domContentLoaded: Math.round(nav ? nav.domContentLoadedEventEnd : 0),
                loadComplete: Math.round(nav ? nav.loadEventEnd : 0),
                fcp: Math.round(fcp ? fcp.startTime : 0),
                transferSize: nav ? nav.transferSize : 0,
            };
        }""")

        if load_time > 3000:
            findings.append({
                'type': 'slow_page_load',
                'load_time_ms': load_time,
                'reason': f'Page took {load_time}ms to load (threshold: 3000ms)',
                'severity': 'medium',
                'url': url,
                'category': 'Performance',
            })

        fcp = metrics.get('fcp', 0)
        if fcp > 1800:
            findings.append({
                'type': 'slow_fcp',
                'fcp_ms': fcp,
                'reason': f'First Contentful Paint {fcp}ms (threshold: 1800ms)',
                'severity': 'low',
                'url': url,
                'category': 'Performance',
            })

        size_kb = round(metrics.get('transferSize', 0) / 1024)
        if size_kb > 2048:
            findings.append({
                'type': 'large_page_size',
                'size_kb': size_kb,
                'reason': f'Page transfer size {size_kb}KB (threshold: 2048KB)',
                'severity': 'low',
                'url': url,
                'category': 'Performance',
            })

        findings.append({
            'type': 'performance_metrics',
            'load_time_ms': load_time,
            'fcp_ms': fcp,
            'dom_content_loaded_ms': metrics.get('domContentLoaded', 0),
            'transfer_size_kb': size_kb,
            'severity': 'info',
            'url': url,
            'category': 'Performance',
        })

    except Exception as e:
        log.warning(f'Performance check failed: {e}')
    return findings


# ── Accessibility ────────────────────────────────────────────────
def check_accessibility(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        # Images missing alt text
        imgs = page.query_selector_all('img:not([alt])')
        if imgs:
            findings.append({
                'type': 'missing_alt_text',
                'count': len(imgs),
                'reason': f'{len(imgs)} image(s) missing alt attribute (WCAG 1.1.1)',
                'severity': 'medium',
                'url': url,
                'category': 'Accessibility',
                'wcag': '1.1.1 Non-text Content',
            })

        # Inputs missing labels
        inputs = page.query_selector_all('input:not([type=hidden]):not([aria-label]):not([id])')
        labeled = 0
        for inp in inputs:
            inp_id = inp.get_attribute('id')
            if inp_id:
                label = page.query_selector(f'label[for="{inp_id}"]')
                if not label:
                    labeled += 1
            else:
                labeled += 1
        if labeled:
            findings.append({
                'type': 'inputs_missing_labels',
                'count': labeled,
                'reason': f'{labeled} input(s) missing associated label (WCAG 1.3.1)',
                'severity': 'medium',
                'url': url,
                'category': 'Accessibility',
                'wcag': '1.3.1 Info and Relationships',
            })

        # Buttons missing accessible text
        btns = page.query_selector_all('button')
        empty_btns = 0
        for btn in btns:
            text = (btn.inner_text() or '').strip()
            aria = btn.get_attribute('aria-label') or ''
            if not text and not aria:
                empty_btns += 1
        if empty_btns:
            findings.append({
                'type': 'buttons_missing_text',
                'count': empty_btns,
                'reason': f'{empty_btns} button(s) have no accessible text (WCAG 4.1.2)',
                'severity': 'medium',
                'url': url,
                'category': 'Accessibility',
                'wcag': '4.1.2 Name, Role, Value',
            })

        # Page missing lang attribute
        lang = page.query_selector('html[lang]')
        if not lang:
            findings.append({
                'type': 'missing_lang_attribute',
                'reason': '<html> element missing lang attribute (WCAG 3.1.1)',
                'severity': 'low',
                'url': url,
                'category': 'Accessibility',
                'wcag': '3.1.1 Language of Page',
            })

        # Skip navigation link
        skip = page.query_selector('a[href="#main"], a[href="#content"], .skip-link')
        if not skip:
            findings.append({
                'type': 'missing_skip_navigation',
                'reason': 'No skip navigation link found (WCAG 2.4.1)',
                'severity': 'low',
                'url': url,
                'category': 'Accessibility',
                'wcag': '2.4.1 Bypass Blocks',
            })

    except Exception as e:
        log.warning(f'Accessibility check failed: {e}')
    return findings


# ── Negative Testing ─────────────────────────────────────────────
def check_negative(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        selectors = get_input_selectors(page)
        if not selectors:
            return findings

        # Test 1: Empty form submission
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=8000)
            page.keyboard.press('Tab')
            submit = page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Sign")')
            if submit and submit.is_visible():
                submit.click(timeout=3000)
                page.wait_for_timeout(1000)
                content = page.content().lower()
                has_validation = any(k in content for k in ['required', 'invalid', 'error', 'please', 'cannot be empty'])
                if not has_validation:
                    findings.append({
                        'type': 'no_empty_form_validation',
                        'reason': 'Form submits without validation on empty fields',
                        'severity': 'medium',
                        'url': url,
                        'category': 'QA – Negative Testing',
                    })
        except Exception:
            pass

        # Test 2: Invalid email format
        email_sel = next((s for s in selectors if 'email' in s.lower()), None)
        if email_sel:
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=8000)
                locator = page.locator(email_sel)
                if locator.is_visible(timeout=2000):
                    locator.fill('notanemail', timeout=3000)
                    page.keyboard.press('Tab')
                    page.wait_for_timeout(500)
                    content = page.content().lower()
                    has_validation = any(k in content for k in ['invalid email', 'valid email', 'email format', '@'])
                    if not has_validation:
                        findings.append({
                            'type': 'no_email_format_validation',
                            'reason': 'Email field accepts invalid format without error',
                            'severity': 'low',
                            'url': url,
                            'category': 'QA – Negative Testing',
                        })
            except Exception:
                pass

        # Test 3: Boundary — max length overflow
        for selector in selectors[:2]:
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=8000)
                locator = page.locator(selector)
                if not locator.is_visible(timeout=2000):
                    continue
                long_input = 'A' * 5000
                locator.fill(long_input, timeout=3000)
                actual = locator.input_value()
                if len(actual) == 5000:
                    findings.append({
                        'type': 'no_max_length_enforcement',
                        'selector': selector,
                        'reason': 'Input field has no maxlength restriction — accepts 5000+ chars',
                        'severity': 'low',
                        'url': url,
                        'category': 'QA – Boundary Testing',
                    })
                break
            except Exception:
                continue

    except Exception as e:
        log.warning(f'Negative testing failed: {e}')
    return findings


# ── Mobile Viewport ──────────────────────────────────────────────
def check_mobile_viewport(page) -> list[dict]:
    findings = []
    url = page.url
    try:
        page.set_viewport_size({'width': 375, 'height': 812})
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(1000)

        # Check viewport meta tag
        viewport_meta = page.query_selector('meta[name="viewport"]')
        if not viewport_meta:
            findings.append({
                'type': 'missing_viewport_meta',
                'reason': 'No viewport meta tag — page not mobile optimized',
                'severity': 'medium',
                'url': url,
                'category': 'QA – Mobile',
            })

        # Check for horizontal scroll
        has_overflow = page.evaluate("""() => document.documentElement.scrollWidth > document.documentElement.clientWidth""")
        if has_overflow:
            findings.append({
                'type': 'horizontal_scroll_on_mobile',
                'reason': 'Page has horizontal overflow on 375px viewport',
                'severity': 'low',
                'url': url,
                'category': 'QA – Mobile',
            })

        # Restore desktop viewport
        page.set_viewport_size({'width': 1920, 'height': 1080})
    except Exception as e:
        log.warning(f'Mobile viewport check failed: {e}')
    return findings


def run_all(page) -> list[dict]:
    """Run all QA checks and return combined findings."""
    all_findings = []
    checks = [
        ('Console Errors', check_console_errors),
        ('Performance', check_performance),
        ('Accessibility', check_accessibility),
        ('Negative Tests', check_negative),
        ('Mobile Viewport', check_mobile_viewport),
    ]
    for name, fn in checks:
        try:
            print(f'    → {name}...', end=' ', flush=True)
            results = fn(page)
            all_findings.extend(results)
            print(f'{len(results)} finding(s)')
        except Exception as e:
            print(f'skipped ({e})')
    return all_findings
