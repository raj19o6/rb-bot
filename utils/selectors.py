from playwright.sync_api import Page


def get_input_selectors(page: Page) -> list[str]:
    """Return CSS selectors for all visible, enabled text-like inputs on the page."""
    handles = page.query_selector_all(
        "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]), textarea"
    )
    selectors = []
    for h in handles:
        id_ = h.get_attribute("id")
        name = h.get_attribute("name")
        if id_:
            selectors.append(f"#{id_}")
        elif name:
            selectors.append(f"[name='{name}']")
    return selectors
