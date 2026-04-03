"""
AI-powered security test case generator.
Uses GPT-3.5-turbo with a Senior AppSec Engineer system prompt.
Outputs structured JSON templates compatible with rb-bot.

Usage:
    from engine.ai_testgen import generate_security_testcases
    cases = generate_security_testcases(url="https://example.com", feature="login", count=3)
"""

import json
import re
from openai import OpenAI
from config.settings import OPENAI_API_KEY
from engine.token_tracker import track_api_call

SYSTEM_PROMPT = """You are a Senior Application Security Engineer with 10+ years of experience in:
- Web application security testing
- OWASP Top 10, OWASP ASVS
- GRC frameworks (ISO 27001, SOC 2, PCI-DSS)

Your task is to generate STRICT, PROFESSIONAL, and AUDIT-READY security test cases.

RULES:
1. Only provide relevant, actionable security test cases.
2. Do NOT include explanations, storytelling, or unnecessary text.
3. Follow EXACT structure for every test case:
   - Test Case ID
   - Title
   - Objective
   - Steps
   - Expected Result
   - Severity
   - Risk
   - Control Mapping
4. Limit output to what is explicitly requested.
5. Do NOT repeat information.
6. Avoid generic statements like "ensure security is maintained".
7. Use precise, technical language.
8. If input is unclear, ask for clarification instead of guessing.

OUTPUT FORMAT MUST BE CONSISTENT AND CLEAN.
NO EXTRA TEXT BEFORE OR AFTER.

Return ONLY a valid JSON array. Each element must follow this schema exactly:
[
  {
    "id": "TC-001",
    "title": "...",
    "objective": "...",
    "steps": ["step 1", "step 2", "..."],
    "expected_result": "...",
    "severity": "Critical|High|Medium|Low",
    "risk": "...",
    "control_mapping": "OWASP A0X / ISO 27001 A.X.X / ..."
  }
]"""


def generate_security_testcases(url: str, feature: str, count: int = 3) -> list[dict]:
    """
    Call GPT-3.5-turbo to generate security test cases for a given URL/feature.
    Returns a list of structured test case dicts.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    user_prompt = (
        f"Generate exactly {count} security test cases for the '{feature}' feature "
        f"at URL: {url}. Focus on OWASP Top 10 risks most relevant to this feature."
    )

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    # Track token usage
    usage = response.usage
    track_api_call(
        model="gpt-3.5-turbo",
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        feature=f"ai_testgen_{feature}"
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


def testcases_to_template(name: str, base_url: str, cases: list[dict]) -> dict:
    """
    Convert AI-generated security test cases into an rb-bot JSON template.
    Each test case becomes a goto + annotated step group.
    """
    steps = [{"action": "goto", "url": base_url}]
    for tc in cases:
        steps.append({
            "action": "security_check",
            "test_case_id": tc["id"],
            "title": tc["title"],
            "objective": tc["objective"],
            "manual_steps": tc["steps"],
            "expected_result": tc["expected_result"],
            "severity": tc["severity"],
            "risk": tc["risk"],
            "control_mapping": tc["control_mapping"],
        })

    return {
        "name": name,
        "generated_by": "ai_testgen",
        "steps": steps,
        "validations": [],
        "security_testcases": cases,
    }
