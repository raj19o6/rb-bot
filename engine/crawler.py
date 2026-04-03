"""
Crawls a website starting from base_url, follows all internal <a href> links,
and returns a deduplicated list of discovered route URLs.
"""

from urllib.parse import urlparse, urljoin, urldefrag
from core.logger import log


def crawl(page, base_url: str, max_depth: int = 2, max_routes: int = 30) -> list[str]:
    base = urlparse(base_url)
    visited = set()
    queue = [(base_url, 0)]
    routes = []

    while queue:
        url, depth = queue.pop(0)
        url, _ = urldefrag(url)  # strip fragments

        if url in visited:
            continue
        if depth > max_depth:
            continue
        if len(routes) >= max_routes:
            break

        visited.add(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(500)
        except Exception as e:
            log.warning(f"Crawler: could not load {url} — {e}")
            continue

        routes.append(url)
        log.info(f"Crawler: [{depth}] {url}")

        if depth < max_depth:
            hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            for href in hrefs:
                href, _ = urldefrag(href)
                parsed = urlparse(href)
                # only follow same-origin links
                if parsed.netloc and parsed.netloc != base.netloc:
                    continue
                absolute = urljoin(base_url, href)
                if absolute not in visited:
                    queue.append((absolute, depth + 1))

    log.info(f"Crawler: discovered {len(routes)} routes")
    return routes
