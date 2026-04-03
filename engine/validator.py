from core.logger import log


def run(page, validations: list) -> list[dict]:
    results = []
    for v in validations:
        vtype = v["type"]
        try:
            if vtype == "url_contains":
                assert v["value"] in page.url, f"URL '{page.url}' missing '{v['value']}'"
            elif vtype == "element_visible":
                assert page.locator(v["selector"]).is_visible()
            elif vtype == "text_present":
                assert v["value"] in page.content()

            log.info(f"✅ validation {vtype} passed")
            results.append({"validation": v, "status": "pass"})

        except AssertionError as e:
            log.error(f"❌ validation {vtype} failed: {e}")
            results.append({"validation": v, "status": "fail", "error": str(e)})

    return results
