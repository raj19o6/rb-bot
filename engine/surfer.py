"""
Surfer — full site intelligence engine.

For every discovered route it collects:
  - Page metadata  (title, description, canonical, og tags)
  - Tech fingerprint (frameworks, CMS, analytics detected from HTML/headers)
  - All interactive elements with XPath + CSS
  - Form map  (each <form> with its fields and action)
  - Asset inventory (scripts, stylesheets, images)
  - Internal + external link lists
  - Security findings (headers, XSS, SQLi)
  - Screenshot (optional)

Returns a structured SurfReport dict consumed by html_reporter.
"""

import re
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag
from core.logger import log
from engine.scraper import scrape
from security import headers as sec_headers, xss as sec_xss, sqli as sec_sqli

ARTIFACTS = Path(__file__).parent.parent / "reports" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

# ── Tech fingerprint signatures ──────────────────────────────────────────────
_TECH_SIGS = {
    "React":          [r"react(?:\.min)?\.js", r"__REACT_DEVTOOLS", r"data-reactroot"],
    "Vue.js":         [r"vue(?:\.min)?\.js", r"__vue__"],
    "Angular":        [r"angular(?:\.min)?\.js", r"ng-version"],
    "Next.js":        [r"_next/static", r"__NEXT_DATA__"],
    "Nuxt.js":        [r"_nuxt/", r"__NUXT__"],
    "jQuery":         [r"jquery(?:\.min)?\.js", r"jQuery\.fn\.jquery"],
    "Bootstrap":      [r"bootstrap(?:\.min)?\.css", r"bootstrap(?:\.min)?\.js"],
    "Tailwind":       [r"tailwind(?:css)?(?:\.min)?\.css", r"tailwindcss"],
    "WordPress":      [r"/wp-content/", r"/wp-includes/"],
    "Django":         [r"csrfmiddlewaretoken", r"django"],
    "Laravel":        [r"laravel_session", r"XSRF-TOKEN"],
    "Google Analytics": [r"google-analytics\.com", r"gtag\(", r"ga\("],
    "Cloudflare":     [r"cloudflare", r"__cf_bm"],
}


def _fingerprint(html: str, response_headers: dict) -> list[str]:
    detected = []
    combined = html + " " + " ".join(str(v) for v in response_headers.values())
    for tech, patterns in _TECH_SIGS.items():
        if any(re.search(p, combined, re.IGNORECASE) for p in patterns):
            detected.append(tech)
    return detected


def _page_meta(page) -> dict:
    return page.evaluate("""() => {
        const g = (sel, attr) => {
            const el = document.querySelector(sel);
            return el ? (attr ? el.getAttribute(attr) : el.textContent.trim()) : '';
        };
        return {
            title:       document.title,
            description: g('meta[name="description"]', 'content'),
            canonical:   g('link[rel="canonical"]', 'href'),
            og_title:    g('meta[property="og:title"]', 'content'),
            og_desc:     g('meta[property="og:description"]', 'content'),
            og_image:    g('meta[property="og:image"]', 'content'),
            robots:      g('meta[name="robots"]', 'content'),
            viewport:    g('meta[name="viewport"]', 'content'),
            charset:     document.characterSet,
            lang:        document.documentElement.lang,
        };
    }""")


def _form_map(page) -> list[dict]:
    return page.evaluate("""() => {
        return Array.from(document.querySelectorAll('form')).map(form => {
            const fields = Array.from(form.querySelectorAll(
                'input:not([type=hidden]), textarea, select'
            )).map(f => ({
                tag:         f.tagName.toLowerCase(),
                type:        f.getAttribute('type') || '',
                name:        f.getAttribute('name') || '',
                id:          f.getAttribute('id') || '',
                placeholder: f.getAttribute('placeholder') || '',
                required:    f.hasAttribute('required'),
            }));
            return {
                action: form.getAttribute('action') || '',
                method: (form.getAttribute('method') || 'GET').toUpperCase(),
                id:     form.getAttribute('id') || '',
                fields,
            };
        });
    }""")


def _assets(page, base_netloc: str) -> dict:
    return page.evaluate(f"""() => {{
        const scripts  = Array.from(document.querySelectorAll('script[src]')).map(e => e.src);
        const styles   = Array.from(document.querySelectorAll('link[rel="stylesheet"]')).map(e => e.href);
        const images   = Array.from(document.querySelectorAll('img[src]')).map(e => e.src);
        const links    = Array.from(document.querySelectorAll('a[href]')).map(e => e.href);
        const internal = links.filter(h => h.includes('{base_netloc}'));
        const external = links.filter(h => h.startsWith('http') && !h.includes('{base_netloc}'));
        return {{ scripts, styles, images, internal_links: internal, external_links: external }};
    }}""")


def _response_headers(page) -> dict:
    try:
        resp = page.evaluate("() => performance.getEntriesByType('navigation')[0]?.serverTiming || []")
        return {}
    except Exception:
        return {}


# ── Main surf function ────────────────────────────────────────────────────────

def surf(page, base_url: str, config: dict) -> dict:
    """
    Full site surf. Returns a SurfReport dict.
    """
    max_depth    = config.get("max_depth", 3)
    max_routes   = config.get("max_routes", 50)
    do_screenshot = config.get("screenshot", True)
    security_checks = config.get("security", ["headers", "xss", "sqli"])

    base = urlparse(base_url)
    visited = set()
    queue   = [(base_url, 0)]
    route_reports = []
    all_routes = []

    print(f"\n  Surfing {base_url} (depth={max_depth}, max={max_routes})")

    while queue and len(all_routes) < max_routes:
        url, depth = queue.pop(0)
        url, _ = urldefrag(url)

        if url in visited or depth > max_depth:
            continue
        visited.add(url)

        # ── Load page ────────────────────────────────────────────────────────
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(400)
        except Exception as e:
            log.warning(f"Surf: skip {url} — {e}")
            continue

        all_routes.append(url)
        print(f"  [{depth}] {url}")

        # ── Collect page intelligence ─────────────────────────────────────
        html      = page.content()
        resp_hdrs = _response_headers(page)
        meta      = _page_meta(page)
        tech      = _fingerprint(html, resp_hdrs)
        forms     = _form_map(page)
        assets    = _assets(page, base.netloc)
        elements  = scrape(page)

        # ── Screenshot ───────────────────────────────────────────────────
        screenshot_path = ""
        if do_screenshot:
            safe_name = re.sub(r"[^\w]", "_", urlparse(url).path.strip("/") or "home")
            shot = ARTIFACTS / f"surf_{safe_name}.png"
            try:
                page.screenshot(path=str(shot), full_page=True)
                screenshot_path = str(shot)
            except Exception:
                pass

        # ── Security checks ───────────────────────────────────────────────
        security_findings = []
        if "headers" in security_checks:
            security_findings += sec_headers.check(page)
        if "xss" in security_checks:
            security_findings += sec_xss.check(page)
        if "sqli" in security_checks:
            security_findings += sec_sqli.check(page)

        route_reports.append({
            "url":          url,
            "depth":        depth,
            "meta":         meta,
            "tech":         tech,
            "forms":        forms,
            "assets":       assets,
            "elements":     elements,
            "security":     security_findings,
            "screenshot":   screenshot_path,
        })

        # ── Enqueue child links ───────────────────────────────────────────
        if depth < max_depth:
            for href in assets.get("internal_links", []):
                href, _ = urldefrag(href)
                parsed  = urlparse(href)
                if parsed.netloc != base.netloc:
                    continue
                absolute = urljoin(base_url, href)
                if absolute not in visited:
                    queue.append((absolute, depth + 1))

    # ── Aggregate tech across all routes ─────────────────────────────────────
    all_tech = sorted(set(t for r in route_reports for t in r["tech"]))
    total_elements = sum(len(r["elements"]) for r in route_reports)
    total_forms    = sum(len(r["forms"])    for r in route_reports)
    total_sec      = sum(len(r["security"]) for r in route_reports)

    print(f"\n  Surf complete: {len(all_routes)} routes | {total_elements} elements | {total_forms} forms | {total_sec} security findings")

    return {
        "template":    "surf_test",
        "base_url":    base_url,
        "routes":      all_routes,
        "route_reports": route_reports,
        "summary": {
            "total_routes":   len(all_routes),
            "total_elements": total_elements,
            "total_forms":    total_forms,
            "total_security": total_sec,
            "tech_stack":     all_tech,
        },
    }
