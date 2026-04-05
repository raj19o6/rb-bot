"""
GRC Report Generator
Maps findings to: OWASP Top 10, ISO 27001, PCI-DSS v4, GDPR, SOC 2
Generates CVSS scores, remediation SLAs, executive summary.
"""
from datetime import datetime, timedelta
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / 'reports'

OWASP_MAP = {
    'missing_header': 'A05:2021 – Security Misconfiguration',
    'weak_csp': 'A03:2021 – Injection',
    'reflected_xss': 'A03:2021 – Injection',
    'dom_xss': 'A03:2021 – Injection',
    'sql_injection': 'A03:2021 – Injection',
    'blind_sql_injection': 'A03:2021 – Injection',
    'missing_csrf_token': 'A01:2021 – Broken Access Control',
    'open_redirect': 'A01:2021 – Broken Access Control',
    'cookie_missing_httponly': 'A02:2021 – Cryptographic Failures',
    'cookie_missing_secure': 'A02:2021 – Cryptographic Failures',
    'cookie_weak_samesite': 'A01:2021 – Broken Access Control',
    'sensitive_data_exposure': 'A02:2021 – Cryptographic Failures',
    'no_rate_limiting': 'A07:2021 – Identification and Authentication Failures',
    'broken_link': 'A05:2021 – Security Misconfiguration',
}

ISO_MAP = {
    'missing_header': 'A.14.1.2 – Securing application services',
    'weak_csp': 'A.14.2.5 – Secure system engineering',
    'reflected_xss': 'A.14.2.5 – Secure system engineering',
    'dom_xss': 'A.14.2.5 – Secure system engineering',
    'sql_injection': 'A.14.2.5 – Secure system engineering',
    'blind_sql_injection': 'A.14.2.5 – Secure system engineering',
    'missing_csrf_token': 'A.14.2.5 – Secure system engineering',
    'open_redirect': 'A.14.2.5 – Secure system engineering',
    'cookie_missing_httponly': 'A.14.1.3 – Protecting application services',
    'cookie_missing_secure': 'A.14.1.3 – Protecting application services',
    'sensitive_data_exposure': 'A.8.2.3 – Handling of assets',
    'no_rate_limiting': 'A.9.4.2 – Secure log-on procedures',
}

PCI_MAP = {
    'missing_header': 'Req 6.4 – Protect web-facing applications',
    'reflected_xss': 'Req 6.3.2 – Protect against common vulnerabilities',
    'sql_injection': 'Req 6.3.2 – Protect against common vulnerabilities',
    'sensitive_data_exposure': 'Req 3.4 – Render PAN unreadable',
    'cookie_missing_secure': 'Req 4.2 – Protect cardholder data in transit',
    'no_rate_limiting': 'Req 8.3 – Secure authentication',
}

GDPR_MAP = {
    'sensitive_data_exposure': 'Art. 32 – Security of processing',
    'cookie_missing_httponly': 'Art. 32 – Security of processing',
    'missing_csrf_token': 'Art. 25 – Data protection by design',
    'no_rate_limiting': 'Art. 32 – Security of processing',
}

CVSS_DEFAULT = {
    'critical': 9.5,
    'high': 7.5,
    'medium': 5.0,
    'low': 2.5,
    'info': 0.0,
}

SLA_DAYS = {
    'critical': 1,
    'high': 7,
    'medium': 30,
    'low': 90,
    'info': 0,
}


def enrich_finding(f: dict) -> dict:
    ftype = f.get('type', '')
    sev = f.get('severity', 'medium').lower()
    f.setdefault('owasp', OWASP_MAP.get(ftype, 'A05:2021 – Security Misconfiguration'))
    f.setdefault('iso27001', ISO_MAP.get(ftype, 'A.12.6.1 – Management of technical vulnerabilities'))
    f.setdefault('pci_dss', PCI_MAP.get(ftype, ''))
    f.setdefault('gdpr', GDPR_MAP.get(ftype, ''))
    f.setdefault('cvss', CVSS_DEFAULT.get(sev, 5.0))
    days = SLA_DAYS.get(sev, 30)
    f.setdefault('remediation_sla', f'{days} day(s)' if days else 'N/A')
    f.setdefault('remediation_due', (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d') if days else 'N/A')
    return f


def generate_grc_report(all_findings: list[dict], workflow_name: str, target_url: str) -> dict:
    enriched = [enrich_finding(dict(f)) for f in all_findings]

    by_severity = {'critical': [], 'high': [], 'medium': [], 'low': [], 'info': []}
    for f in enriched:
        sev = f.get('severity', 'medium').lower()
        by_severity.setdefault(sev, []).append(f)

    owasp_counts = {}
    for f in enriched:
        o = f.get('owasp', 'Unknown')
        owasp_counts[o] = owasp_counts.get(o, 0) + 1

    total = len(enriched)
    critical_count = len(by_severity['critical'])
    high_count = len(by_severity['high'])
    risk_score = min(100, round((critical_count * 10 + high_count * 5 + len(by_severity['medium']) * 2) / max(1, total) * 20))

    risk_level = 'CRITICAL' if critical_count > 0 else 'HIGH' if high_count > 0 else 'MEDIUM' if by_severity['medium'] else 'LOW'

    return {
        'workflow_name': workflow_name,
        'target_url': target_url,
        'generated_at': datetime.now().isoformat(),
        'risk_level': risk_level,
        'risk_score': risk_score,
        'total_findings': total,
        'by_severity': {k: len(v) for k, v in by_severity.items()},
        'owasp_breakdown': owasp_counts,
        'findings': enriched,
        'compliance': {
            'owasp_top10': _compliance_status(enriched, 'owasp'),
            'iso27001': _compliance_status(enriched, 'iso27001'),
            'pci_dss': _compliance_status(enriched, 'pci_dss'),
            'gdpr': _compliance_status(enriched, 'gdpr'),
        },
        'executive_summary': _executive_summary(workflow_name, target_url, enriched, risk_level, risk_score),
    }


def _compliance_status(findings, framework_key):
    violations = [f for f in findings if f.get(framework_key) and f.get('severity') in ('critical', 'high')]
    return {
        'status': 'FAIL' if violations else 'PASS',
        'violations': len(violations),
        'items': list({f[framework_key] for f in violations}),
    }


def _executive_summary(name, url, findings, risk_level, score):
    critical = [f for f in findings if f.get('severity') == 'critical']
    high = [f for f in findings if f.get('severity') == 'high']
    lines = [
        f"Security assessment of '{name}' ({url}) completed on {datetime.now().strftime('%Y-%m-%d')}.",
        f"Overall Risk Level: {risk_level} (Score: {score}/100).",
        f"Total findings: {len(findings)} ({len(critical)} critical, {len(high)} high).",
    ]
    if critical:
        lines.append(f"IMMEDIATE ACTION REQUIRED: {', '.join(set(f['type'].replace('_',' ') for f in critical[:3]))}.")
    if high:
        lines.append(f"High priority issues: {', '.join(set(f['type'].replace('_',' ') for f in high[:3]))}.")
    lines.append("Remediation SLAs: Critical=24h, High=7d, Medium=30d, Low=90d.")
    return ' '.join(lines)


def generate_grc_html(grc: dict) -> str:
    sev_colors = {'critical': '#7c3aed', 'high': '#ef4444', 'medium': '#f97316', 'low': '#eab308', 'info': '#64748b'}
    risk_colors = {'CRITICAL': '#7c3aed', 'HIGH': '#ef4444', 'MEDIUM': '#f97316', 'LOW': '#22c55e'}
    risk_color = risk_colors.get(grc['risk_level'], '#64748b')

    # Compliance cards
    compliance_html = ''
    for framework, data in grc['compliance'].items():
        color = '#22c55e' if data['status'] == 'PASS' else '#ef4444'
        items_html = ''.join(f'<li style="color:#94a3b8;font-size:11px;margin:2px 0">{i}</li>' for i in data['items'][:5])
        compliance_html += f"""
        <div style="background:#0f172a;border-radius:8px;padding:16px;border-top:3px solid {color}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:#f1f5f9;font-weight:600;font-size:13px">{framework.upper().replace('_',' ')}</span>
                <span style="background:{color};color:#fff;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700">{data['status']}</span>
            </div>
            <div style="color:#64748b;font-size:11px;margin-top:4px">{data['violations']} violation(s)</div>
            <ul style="margin-top:6px;padding-left:14px">{items_html}</ul>
        </div>"""

    # OWASP breakdown
    owasp_html = ''
    for owasp, count in sorted(grc['owasp_breakdown'].items(), key=lambda x: -x[1]):
        owasp_html += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #1e293b">
            <span style="color:#94a3b8;font-size:12px">{owasp}</span>
            <span style="background:#1e293b;color:#f1f5f9;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600">{count}</span>
        </div>"""

    # Findings table
    findings_html = ''
    for f in grc['findings']:
        if f.get('severity') == 'info':
            continue
        sev = f.get('severity', 'medium')
        color = sev_colors.get(sev, '#64748b')
        findings_html += f"""
        <tr>
            <td style="padding:8px 12px"><span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600">{sev.upper()}</span></td>
            <td style="padding:8px 12px;color:#cbd5e1;font-size:12px">{f.get('type','').replace('_',' ').title()}</td>
            <td style="padding:8px 12px;color:#94a3b8;font-size:11px">{f.get('owasp','')}</td>
            <td style="padding:8px 12px;color:#94a3b8;font-size:11px">{f.get('iso27001','')}</td>
            <td style="padding:8px 12px;color:#f1f5f9;font-size:11px;font-weight:600">{f.get('cvss','')}</td>
            <td style="padding:8px 12px;color:#fbbf24;font-size:11px">{f.get('remediation_sla','')}</td>
            <td style="padding:8px 12px;color:#64748b;font-size:11px">{f.get('reason','')[:80]}</td>
        </tr>"""

    severity_bars = ''
    for sev, color in sev_colors.items():
        count = grc['by_severity'].get(sev, 0)
        if sev == 'info':
            continue
        severity_bars += f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
            <span style="width:70px;color:#94a3b8;font-size:12px;text-align:right">{sev.upper()}</span>
            <div style="flex:1;background:#1e293b;border-radius:4px;height:20px;overflow:hidden">
                <div style="width:{min(100, count*10)}%;height:100%;background:{color};display:flex;align-items:center;padding-left:8px">
                    <span style="color:#fff;font-size:11px;font-weight:700">{count}</span>
                </div>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GRC Security Report – {grc['workflow_name']}</title>
<style>
* {{ box-sizing:border-box;margin:0;padding:0 }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;padding:32px }}
table tr:hover {{ background:rgba(255,255,255,0.03) }}
</style>
</head>
<body>
<header style="margin-bottom:32px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px">
        <div>
            <h1 style="font-size:26px;font-weight:700;color:#f1f5f9">🛡️ GRC Security Report</h1>
            <p style="color:#64748b;margin-top:4px">{grc['workflow_name']} — <a href="{grc['target_url']}" style="color:#7dd3fc">{grc['target_url']}</a></p>
            <p style="color:#475569;font-size:12px;margin-top:4px">Generated: {grc['generated_at'][:19].replace('T',' ')}</p>
        </div>
        <div style="background:#1e293b;border-radius:12px;padding:20px 32px;text-align:center;border-top:4px solid {risk_color}">
            <div style="font-size:36px;font-weight:800;color:{risk_color}">{grc['risk_level']}</div>
            <div style="color:#64748b;font-size:12px;margin-top:4px">RISK LEVEL</div>
            <div style="font-size:22px;font-weight:700;color:#f1f5f9;margin-top:8px">{grc['risk_score']}/100</div>
            <div style="color:#64748b;font-size:11px">RISK SCORE</div>
        </div>
    </div>
</header>

<div style="background:#1e293b;border-radius:10px;padding:20px;margin-bottom:24px">
    <h2 style="color:#f1f5f9;font-size:16px;margin-bottom:12px">📋 Executive Summary</h2>
    <p style="color:#94a3b8;font-size:13px;line-height:1.7">{grc['executive_summary']}</p>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px">
    <div style="background:#1e293b;border-radius:10px;padding:20px">
        <h2 style="color:#f1f5f9;font-size:15px;margin-bottom:16px">📊 Findings by Severity</h2>
        {severity_bars}
    </div>
    <div style="background:#1e293b;border-radius:10px;padding:20px">
        <h2 style="color:#f1f5f9;font-size:15px;margin-bottom:16px">🎯 OWASP Top 10 Breakdown</h2>
        {owasp_html}
    </div>
</div>

<div style="background:#1e293b;border-radius:10px;padding:20px;margin-bottom:24px">
    <h2 style="color:#f1f5f9;font-size:15px;margin-bottom:16px">✅ Compliance Status</h2>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px">
        {compliance_html}
    </div>
</div>

<div style="background:#1e293b;border-radius:10px;padding:20px;margin-bottom:24px">
    <h2 style="color:#f1f5f9;font-size:15px;margin-bottom:16px">🔍 Detailed Findings</h2>
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden">
        <thead><tr style="background:#1e293b;color:#94a3b8;font-size:12px">
            <th style="padding:10px 12px;text-align:left">Severity</th>
            <th style="padding:10px 12px;text-align:left">Finding</th>
            <th style="padding:10px 12px;text-align:left">OWASP</th>
            <th style="padding:10px 12px;text-align:left">ISO 27001</th>
            <th style="padding:10px 12px;text-align:left">CVSS</th>
            <th style="padding:10px 12px;text-align:left">SLA</th>
            <th style="padding:10px 12px;text-align:left">Detail</th>
        </tr></thead>
        <tbody>{findings_html}</tbody>
    </table>
    </div>
</div>

<footer style="text-align:center;color:#334155;font-size:11px;margin-top:32px">
    Generated by RB-BOT Security Engine · Confidential · {datetime.now().strftime('%Y-%m-%d')}
</footer>
</body>
</html>"""


def save_grc_report(grc: dict, workflow_name: str) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    html_content = generate_grc_html(grc)
    safe_name = workflow_name.replace(' ', '_').lower()
    path = REPORTS_DIR / f'grc_{safe_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    path.write_text(html_content, encoding='utf-8')
    return path
