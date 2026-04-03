import re


def substitute(text: str, variables: dict) -> str:
    """Replace {{key}} placeholders with values from variables dict."""
    for k, v in variables.items():
        text = text.replace(f"{{{{{k}}}}}", str(v))
    return text


def is_error_page(content: str) -> bool:
    """Detect common DB/server error strings in page content."""
    patterns = [
        r"sql syntax", r"mysql_fetch", r"ORA-\d+", r"pg_query",
        r"unclosed quotation", r"syntax error", r"warning: mysql",
        r"division by zero", r"stack trace", r"internal server error",
    ]
    lower = content.lower()
    return any(re.search(p, lower) for p in patterns)


def truncate(text: str, max_len: int = 120) -> str:
    return text if len(text) <= max_len else text[:max_len] + "..."
