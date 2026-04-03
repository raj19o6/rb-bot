import json
from pathlib import Path
from core import browser
from engine import template_loader, executor, validator
from engine.ai_testgen import generate_security_testcases
from engine.crawler import crawl
from engine.auto_runner import run_route
from engine.surfer import surf
from reports.report_generator import save
from reports.html_reporter import generate
from security import headers, xss, sqli

INPUT = Path(__file__).parent.parent / "data" / "input.json"


def run_bot():
    data = json.loads(INPUT.read_text())
    variables       = {k: v for k, v in data.items() if k not in ("templates", "openai_api_key", "ai_testgen", "crawl", "surf")}
    security_checks = data.get("security", ["headers", "xss", "sqli"])
    ai_cfg          = data.get("ai_testgen", {})
    crawl_cfg       = data.get("crawl", {})
    surf_cfg        = data.get("surf", {})
    page            = browser.get_page()
    all_reports     = []
    surf_reports    = []

    try:
        # ── Surf mode ────────────────────────────────────────────────────────
        if surf_cfg.get("enabled"):
            surf_result = surf(page, data["base_url"], surf_cfg)
            surf_reports.append(surf_result)

        # ── Crawl mode ───────────────────────────────────────────────────────
        if crawl_cfg.get("enabled"):
            print(f"\n  Crawling {data['base_url']} ...")
            routes = crawl(
                page,
                base_url=data["base_url"],
                max_depth=crawl_cfg.get("max_depth", 2),
                max_routes=crawl_cfg.get("max_routes", 20),
            )
            print(f"   Found {len(routes)} routes")
            for route_url in routes:
                print(f"\n  Auto-testing: {route_url}")
                report = run_route(page, route_url, security_checks)
                if report:
                    report["security_testcases"] = []
                    all_reports.append(report)

        # ── Template mode ────────────────────────────────────────────────────
        for tmpl_name in data.get("templates", []):
            print(f"\n  Running: {tmpl_name}")
            tmpl        = template_loader.load(tmpl_name, variables)
            steps       = executor.run(page, tmpl["steps"], variables)
            validations = validator.run(page, tmpl.get("validations", []))

            security_findings = []
            if "headers" in security_checks:
                security_findings += headers.check(page)
            if "xss" in security_checks:
                security_findings += xss.check(page)
            if "sqli" in security_checks:
                security_findings += sqli.check(page)

            ai_cases = []
            if data.get("openai_api_key") and ai_cfg:
                try:
                    print(f"   Generating AI security test cases...")
                    ai_cases = generate_security_testcases(
                        url=data["base_url"],
                        feature=ai_cfg.get("feature", tmpl_name),
                        count=ai_cfg.get("count", 3),
                    )
                    print(f"   {len(ai_cases)} AI test cases generated")
                except Exception as e:
                    print(f"   AI testgen skipped: {e}")

            report = save(tmpl_name, steps, validations, security_findings)
            report["security_testcases"] = ai_cases
            all_reports.append(report)

    finally:
        browser.close()
        generate(all_reports, surf_reports)


if __name__ == "__main__":
    run_bot()
