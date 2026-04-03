import json
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent


def save(template_name: str, step_results: list, validation_results: list, security_findings: list = None):
    security_findings = security_findings or []

    passed = sum(1 for r in step_results + validation_results if r["status"] == "pass")
    total = len(step_results) + len(validation_results)

    critical = [f for f in security_findings if f.get("severity") == "critical"]
    high     = [f for f in security_findings if f.get("severity") == "high"]
    medium   = [f for f in security_findings if f.get("severity") == "medium"]

    report = {
        "template": template_name,
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "passed": passed,
            "failed": total - passed,
            "total": total,
            "security_issues": len(security_findings),
        },
        "steps": step_results,
        "validations": validation_results,
        "security": {
            "critical": critical,
            "high": high,
            "medium": medium,
        },
    }

    out = REPORTS_DIR / f"{template_name}_{datetime.now().strftime('%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=2))

    print(f"\n📄 Report: {out}")
    print(f"   ✅ {passed}/{total} passed")
    if security_findings:
        print(f"   🔐 Security: {len(critical)} critical, {len(high)} high, {len(medium)} medium")

    return report
