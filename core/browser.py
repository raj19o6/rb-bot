from playwright.sync_api import sync_playwright
from config.settings import BROWSER, HEADLESS, TIMEOUT, SLOW_MO

_pw = None
_browser = None


def get_page():
    global _pw, _browser
    _pw = sync_playwright().start()
    launcher = getattr(_pw, BROWSER)
    _browser = launcher.launch(headless=HEADLESS, slow_mo=SLOW_MO)
    ctx = _browser.new_context()
    page = ctx.new_page()
    page.set_default_timeout(TIMEOUT)
    return page


def close():
    if _browser:
        _browser.close()
    if _pw:
        _pw.stop()
