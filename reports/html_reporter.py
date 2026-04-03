from pathlib import Path
from datetime import datetime

REPORTS_DIR = Path(__file__).parent


def generate(all_reports: list[dict], surf_reports: list[dict] = None):

    def badge(status):
        color = "#22c55e" if status == "pass" else "#ef4444"
        return f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600">{status.upper()}</span>'

    def sev_badge(sev):
        colors = {"critical": "#7c3aed", "high": "#ef4444", "medium": "#f97316", "low": "#eab308"}
        c = colors.get(sev.lower(), "#6b7280")
        return f'<span style="background:{c};color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600">{sev.upper()}</span>'

    def flow_icon(action):
        icons = {
            "goto":           '<i data-lucide="globe"          style="width:16px;height:16px;stroke:#94a3b8"></i>',
            "fill":           '<i data-lucide="pencil"         style="width:16px;height:16px;stroke:#94a3b8"></i>',
            "click":          '<i data-lucide="mouse-pointer-2"style="width:16px;height:16px;stroke:#94a3b8"></i>',
            "press":          '<i data-lucide="keyboard"       style="width:16px;height:16px;stroke:#94a3b8"></i>',
            "wait":           '<i data-lucide="timer"          style="width:16px;height:16px;stroke:#94a3b8"></i>',
            "security_check": '<i data-lucide="shield-alert"   style="width:16px;height:16px;stroke:#94a3b8"></i>',
        }
        return icons.get(action, '<i data-lucide="play" style="width:16px;height:16px;stroke:#94a3b8"></i>')

    def build_flow(steps):
        nodes = ""
        for i, r in enumerate(steps):
            step = r["step"]
            action = step["action"]
            is_pass = r["status"] == "pass"
            color = "#22c55e" if is_pass else "#ef4444"
            detail = step.get("url") or step.get("selector", step.get("title", ""))
            value = f'<div style="color:#94a3b8;font-size:11px;margin-top:3px">{step["value"]}</div>' if "value" in step else ""
            err = f'<div style="color:#ef4444;font-size:10px;margin-top:4px;max-width:180px;word-break:break-word">{r.get("error","")[:80]}...</div>' if r.get("error") else ""
            connector = '<div style="width:32px;height:2px;background:#334155;flex-shrink:0"></div>' if i < len(steps) - 1 else ""
            nodes += f"""
            <div style="display:flex;align-items:center;gap:0">
              <div style="border:2px solid {color};border-radius:10px;padding:10px 14px;background:#0f172a;min-width:140px;max-width:200px;position:relative">
                <div style="margin-bottom:6px">{flow_icon(action)}</div>
                <div style="font-size:12px;font-weight:600;color:#f1f5f9">{action.upper()}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;word-break:break-all">{detail}</div>
                {value}{err}
                <div style="position:absolute;top:6px;right:8px;width:8px;height:8px;border-radius:50%;background:{color}"></div>
              </div>
              {connector}
            </div>"""
        return nodes

    def build_ai_testcases(cases):
        if not cases:
            return ""
        rows = ""
        for tc in cases:
            sev = tc.get("severity", "medium").lower()
            left_color = "#ef4444" if sev == "high" else "#7c3aed" if sev == "critical" else "#f97316" if sev == "medium" else "#eab308"
            steps_html = "".join(f'<li style="margin:3px 0;color:#94a3b8;font-size:12px">{s}</li>' for s in tc.get("steps", []))
            rows += f"""
            <div style="background:#0f172a;border-radius:8px;padding:16px;margin-bottom:12px;border-left:3px solid {left_color}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
                <div>
                  <span style="color:#64748b;font-size:11px;font-weight:600">{tc.get('id','')}</span>
                  <div style="color:#f1f5f9;font-size:14px;font-weight:600;margin-top:2px">{tc.get('title','')}</div>
                  <div style="color:#64748b;font-size:12px;margin-top:4px">{tc.get('objective','')}</div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
                  {sev_badge(tc.get('severity','medium'))}
                  <span style="color:#64748b;font-size:10px">{tc.get('control_mapping','')}</span>
                </div>
              </div>
              <div style="margin-top:10px">
                <div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:4px">STEPS</div>
                <ol style="padding-left:16px">{steps_html}</ol>
              </div>
              <div style="display:flex;gap:24px;margin-top:10px;flex-wrap:wrap">
                <div><span style="color:#64748b;font-size:11px">EXPECTED: </span><span style="color:#cbd5e1;font-size:12px">{tc.get('expected_result','')}</span></div>
                <div><span style="color:#64748b;font-size:11px">RISK: </span><span style="color:#cbd5e1;font-size:12px">{tc.get('risk','')}</span></div>
              </div>
            </div>"""
        return f"""
        <h3 style="color:#a78bfa;margin:28px 0 12px;display:flex;align-items:center;gap:8px">
          <i data-lucide="bot" style="width:16px;height:16px;stroke:#a78bfa"></i>
          AI-Generated Security Test Cases ({len(cases)})
        </h3>
        {rows}"""

    def build_elements_table(elements):
        if not elements:
            return ""
        rows = ""
        for el in elements:
            tag_badge = f'<code style="background:#1e293b;padding:2px 8px;border-radius:4px;font-size:11px">{el["tag"]}{"["+el["type"]+"]" if el["type"] else ""}</code>'
            css  = f'<code style="color:#7dd3fc;font-size:11px">{el["css"]}</code>'
            xpath = f'<code style="color:#a78bfa;font-size:10px;word-break:break-all">{el["xpath"]}</code>' if el["xpath"] else ""
            hint = el.get("placeholder") or el.get("text") or el.get("name") or ""
            rows += f"""
            <tr>
              <td style="padding:7px 12px">{tag_badge}</td>
              <td style="padding:7px 12px">{css}</td>
              <td style="padding:7px 12px">{xpath}</td>
              <td style="padding:7px 12px;color:#64748b;font-size:12px">{hint[:50]}</td>
            </tr>"""
        return f"""
        <h3 style="color:#94a3b8;margin:24px 0 12px;display:flex;align-items:center;gap:8px">
          <i data-lucide="scan-search" style="width:15px;height:15px;stroke:#94a3b8"></i>
          Scraped Elements ({len(elements)})
        </h3>
        <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
          <thead><tr style="background:#1e293b;color:#94a3b8;font-size:12px">
            <th style="padding:9px 12px;text-align:left">Element</th>
            <th style="padding:9px 12px;text-align:left">CSS Selector</th>
            <th style="padding:9px 12px;text-align:left">XPath</th>
            <th style="padding:9px 12px;text-align:left">Hint</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    surf_section = ""
    if surf_reports:
        for surf in surf_reports:
            rows = ""
            for route in surf.get("route_reports", []):
                meta = route.get("meta", {})
                rows += f"""
                <tr>
                  <td style="padding:8px 12px;color:#cbd5e1">{route["url"]}</td>
                  <td style="padding:8px 12px;color:#94a3b8">{meta.get("title", "-")}</td>
                  <td style="padding:8px 12px;color:#64748b;font-size:11px">{meta.get("description", "-")[:80]}</td>
                  <td style="padding:8px 12px;text-align:center"><code style="background:#1e293b;padding:2px 8px;border-radius:4px;font-size:11px">{len(route.get("forms", []))}</code></td>
                  <td style="padding:8px 12px;text-align:center"><code style="background:#1e293b;padding:2px 8px;border-radius:4px;font-size:11px">{len([e for e in route.get("elements", []) if e.get("tag") in ["input", "textarea", "select"]])}</code></td>
                  <td style="padding:8px 12px;text-align:center"><code style="background:#1e293b;padding:2px 8px;border-radius:4px;font-size:11px">{len([e for e in route.get("elements", []) if e.get("tag") == "button"])}</code></td>
                </tr>"""
            surf_section = f"""
            <section style="background:#1e293b;border-radius:12px;padding:28px;margin-bottom:32px">
              <h2 style="margin:0 0 16px;color:#f1f5f9;font-size:20px;display:flex;align-items:center;gap:8px">
                <i data-lucide="waves" style="width:18px;height:18px;stroke:#06b6d4"></i>
                Surf Report
              </h2>
              <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
                <thead><tr style="background:#1e293b;color:#94a3b8;font-size:13px">
                  <th style="padding:10px 12px;text-align:left">URL</th>
                  <th style="padding:10px 12px;text-align:left">Title</th>
                  <th style="padding:10px 12px;text-align:left">Description</th>
                  <th style="padding:10px 12px;text-align:center">Forms</th>
                  <th style="padding:10px 12px;text-align:center">Inputs</th>
                  <th style="padding:10px 12px;text-align:center">Buttons</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </section>"""

    sections = ""
    for report in all_reports:
        tmpl = report["template"]
        ts = report["timestamp"]
        s = report["summary"]
        steps = report["steps"]
        validations = report["validations"]
        sec = report["security"]
        all_sec = sec["critical"] + sec["high"] + sec["medium"]
        ai_cases = report.get("security_testcases", [])
        elements  = report.get("elements", [])
        route_url = report.get("url", "")

        flow_nodes = build_flow(steps)

        step_rows = ""
        for i, r in enumerate(steps, 1):
            step = r["step"]
            if step["action"] == "security_check":
                continue
            detail = step.get("url") or step.get("selector", "")
            value = f' &rarr; <code>{step["value"]}</code>' if "value" in step else ""
            key = f' &rarr; <code>{step["key"]}</code>' if "key" in step else ""
            err = f'<br><small style="color:#ef4444">{r.get("error","")}</small>' if r["status"] == "fail" else ""
            step_rows += f"""
            <tr>
              <td style="padding:8px 12px;color:#94a3b8">{i}</td>
              <td style="padding:8px 12px"><code style="background:#1e293b;padding:2px 8px;border-radius:4px">{step["action"]}</code></td>
              <td style="padding:8px 12px;color:#cbd5e1">{detail}{value}{key}{err}</td>
              <td style="padding:8px 12px">{badge(r["status"])}</td>
            </tr>"""

        val_rows = ""
        for r in validations:
            v = r["validation"]
            err = f'<br><small style="color:#ef4444">{r.get("error","")}</small>' if r["status"] == "fail" else ""
            val_rows += f"""
            <tr>
              <td style="padding:8px 12px"><code style="background:#1e293b;padding:2px 8px;border-radius:4px">{v["type"]}</code></td>
              <td style="padding:8px 12px;color:#cbd5e1"><code>{v.get("value", v.get("selector",""))}</code>{err}</td>
              <td style="padding:8px 12px">{badge(r["status"])}</td>
            </tr>"""

        sec_rows = ""
        for f in all_sec:
            ftype = f["type"].replace("_", " ").title()
            detail = f.get("header") or f.get("selector") or ""
            payload = f'<br><code style="color:#fca5a5;font-size:11px">{f["payload"]}</code>' if "payload" in f else ""
            reason = f.get("reason", "")
            sec_rows += f"""
            <tr>
              <td style="padding:8px 12px">{sev_badge(f["severity"])}</td>
              <td style="padding:8px 12px;color:#cbd5e1">{ftype}</td>
              <td style="padding:8px 12px;color:#94a3b8">{detail}{payload}</td>
              <td style="padding:8px 12px;color:#94a3b8">{reason}</td>
            </tr>"""

        sec_section = f"""
        <h3 style="color:#f97316;margin:28px 0 12px;display:flex;align-items:center;gap:8px">
          <i data-lucide="shield" style="width:16px;height:16px;stroke:#f97316"></i>
          Security Findings ({len(all_sec)})
        </h3>
        <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
          <thead><tr style="background:#1e293b;color:#94a3b8;font-size:13px">
            <th style="padding:10px 12px;text-align:left">Severity</th>
            <th style="padding:10px 12px;text-align:left">Type</th>
            <th style="padding:10px 12px;text-align:left">Target</th>
            <th style="padding:10px 12px;text-align:left">Reason</th>
          </tr></thead>
          <tbody>{sec_rows}</tbody>
        </table>""" if all_sec else '<p style="color:#22c55e;margin-top:16px;display:flex;align-items:center;gap:6px"><i data-lucide="check-circle" style="width:14px;height:14px;stroke:#22c55e"></i> No security issues found.</p>'

        pass_rate = round((s["passed"] / s["total"]) * 100) if s["total"] else 0
        bar_color = "#22c55e" if pass_rate == 100 else "#f97316" if pass_rate >= 50 else "#ef4444"

        sections += f"""
        <section style="background:#1e293b;border-radius:12px;padding:28px;margin-bottom:32px">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px">
            <div>
              <h2 style="margin:0;color:#f1f5f9;font-size:20px;display:flex;align-items:center;gap:8px">
                <i data-lucide="clipboard-list" style="width:18px;height:18px;stroke:#f1f5f9"></i>
                {tmpl}
              </h2>
              <p style="margin:4px 0 0;color:#64748b;font-size:13px">{ts}</p>
              {f'<a href="{route_url}" target="_blank" style="display:inline-flex;align-items:center;gap:4px;margin-top:6px;color:#7dd3fc;font-size:11px;text-decoration:none">{route_url}</a>' if route_url else ''}
            </div>
            <div style="display:flex;gap:16px;align-items:center">
              <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#22c55e">{s["passed"]}</div><div style="font-size:11px;color:#64748b">PASSED</div></div>
              <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#ef4444">{s["failed"]}</div><div style="font-size:11px;color:#64748b">FAILED</div></div>
              <div style="text-align:center"><div style="font-size:24px;font-weight:700;color:#f97316">{s["security_issues"]}</div><div style="font-size:11px;color:#64748b">SEC ISSUES</div></div>
            </div>
          </div>
          <div style="margin:16px 0;background:#0f172a;border-radius:6px;height:8px;overflow:hidden">
            <div style="width:{pass_rate}%;height:100%;background:{bar_color};transition:width 0.3s"></div>
          </div>

          <h3 style="color:#94a3b8;margin:24px 0 12px;display:flex;align-items:center;gap:8px">
            <i data-lucide="git-branch" style="width:15px;height:15px;stroke:#94a3b8"></i>
            Test Flow
          </h3>
          <div style="display:flex;align-items:flex-start;gap:0;overflow-x:auto;padding:12px 0;flex-wrap:nowrap">
            {flow_nodes}
          </div>

          <h3 style="color:#94a3b8;margin:24px 0 12px;display:flex;align-items:center;gap:8px">
            <i data-lucide="flask-conical" style="width:15px;height:15px;stroke:#94a3b8"></i>
            Test Steps
          </h3>
          <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
            <thead><tr style="background:#1e293b;color:#94a3b8;font-size:13px">
              <th style="padding:10px 12px;text-align:left">#</th>
              <th style="padding:10px 12px;text-align:left">Action</th>
              <th style="padding:10px 12px;text-align:left">Target / Value</th>
              <th style="padding:10px 12px;text-align:left">Status</th>
            </tr></thead>
            <tbody>{step_rows}</tbody>
          </table>

          <h3 style="color:#94a3b8;margin:24px 0 12px;display:flex;align-items:center;gap:8px">
            <i data-lucide="check-square" style="width:15px;height:15px;stroke:#94a3b8"></i>
            Validations
          </h3>
          <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
            <thead><tr style="background:#1e293b;color:#94a3b8;font-size:13px">
              <th style="padding:10px 12px;text-align:left">Type</th>
              <th style="padding:10px 12px;text-align:left">Expected</th>
              <th style="padding:10px 12px;text-align:left">Status</th>
            </tr></thead>
            <tbody>{val_rows}</tbody>
          </table>

          {sec_section}
          {build_elements_table(elements)}
          {build_ai_testcases(ai_cases)}
        </section>"""

    total_passed = sum(r["summary"]["passed"] for r in all_reports)
    total_failed = sum(r["summary"]["failed"] for r in all_reports)
    total_sec = sum(r["summary"]["security_issues"] for r in all_reports)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>rb-bot Report</title>
  <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 32px; }}
    code {{ font-family: 'SF Mono', 'Fira Code', monospace; }}
    table tr:hover {{ background: rgba(255,255,255,0.03); }}
  </style>
</head>
<body>
  <header style="margin-bottom:36px">
    <h1 style="font-size:28px;font-weight:700;color:#f1f5f9;display:flex;align-items:center;gap:10px">
      <i data-lucide="bot" style="width:28px;height:28px;stroke:#6366f1"></i>
      rb-bot Test Report
    </h1>
    <p style="color:#64748b;margin-top:6px;display:flex;align-items:center;gap:6px">
      <i data-lucide="calendar" style="width:13px;height:13px;stroke:#64748b"></i>
      Generated: {now}
    </p>
    <div style="display:flex;gap:24px;margin-top:20px;flex-wrap:wrap">
      <div style="background:#1e293b;border-radius:10px;padding:16px 24px;text-align:center">
        <div style="font-size:32px;font-weight:700;color:#22c55e">{total_passed}</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px">TOTAL PASSED</div>
      </div>
      <div style="background:#1e293b;border-radius:10px;padding:16px 24px;text-align:center">
        <div style="font-size:32px;font-weight:700;color:#ef4444">{total_failed}</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px">TOTAL FAILED</div>
      </div>
      <div style="background:#1e293b;border-radius:10px;padding:16px 24px;text-align:center">
        <div style="font-size:32px;font-weight:700;color:#f97316">{total_sec}</div>
        <div style="font-size:12px;color:#64748b;margin-top:4px">SECURITY ISSUES</div>
      </div>
    </div>
  </header>
  {surf_section}
  {sections}
  <script>lucide.createIcons();</script>
</body>
</html>"""

    out = REPORTS_DIR / "report.html"
    out.write_text(html)
    print(f"\n  HTML Report: {out}")
    return out
