"""
Scrapes all interactive elements from a loaded page.
Returns XPath, CSS selector, tag, type, name, placeholder, and text for each element.
"""

from core.logger import log


_XPATH_JS = """
(el) => {
    const parts = [];
    let node = el;
    while (node && node.nodeType === 1) {
        let idx = 1;
        let sib = node.previousSibling;
        while (sib) {
            if (sib.nodeType === 1 && sib.tagName === node.tagName) idx++;
            sib = sib.previousSibling;
        }
        const tag = node.tagName.toLowerCase();
        const id = node.getAttribute('id');
        if (id) {
            parts.unshift(`//${tag}[@id='${id}']`);
            break;
        }
        parts.unshift(`${tag}[${idx}]`);
        node = node.parentNode;
    }
    return parts.length ? '/' + parts.join('/') : '';
}
"""

_INTERACTIVE = (
    "input:not([type=hidden]), "
    "textarea, "
    "select, "
    "button, "
    "a[href], "
    "[role=button], "
    "[role=link], "
    "[role=textbox]"
)


def scrape(page) -> list[dict]:
    elements = []
    try:
        handles = page.query_selector_all(_INTERACTIVE)
        for h in handles:
            try:
                if not h.is_visible():
                    continue
                tag      = (h.evaluate("e => e.tagName") or "").lower()
                el_type  = h.get_attribute("type") or ""
                el_id    = h.get_attribute("id") or ""
                name     = h.get_attribute("name") or ""
                placeholder = h.get_attribute("placeholder") or ""
                text     = (h.inner_text() or "").strip()[:60]
                href     = h.get_attribute("href") or ""
                xpath    = h.evaluate(_XPATH_JS) or ""

                # build best CSS selector
                if el_id:
                    css = f"#{el_id}"
                elif name:
                    css = f"[name='{name}']"
                elif el_type:
                    css = f"{tag}[type='{el_type}']"
                else:
                    css = tag

                elements.append({
                    "tag":         tag,
                    "type":        el_type,
                    "id":          el_id,
                    "name":        name,
                    "placeholder": placeholder,
                    "text":        text,
                    "href":        href,
                    "xpath":       xpath,
                    "css":         css,
                })
            except Exception:
                continue
    except Exception as e:
        log.warning(f"Scraper error: {e}")

    log.info(f"Scraper: found {len(elements)} interactive elements on {page.url}")
    return elements
