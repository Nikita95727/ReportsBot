import re
from typing import Optional


def parse_report(text: str) -> dict:
    """
    Parse a /report message into structured sections.

    Returns dict with keys:
        done: str | None
        problems: str | None
        plan: str | None
        has_report: bool  (done section exists)
        has_plan: bool    (plan section exists)
        format_valid: bool (done + plan both present)
        raw_text: str
    """
    # Remove the /report command prefix
    clean = re.sub(r"^/report\s*", "", text, flags=re.IGNORECASE).strip()

    done = _extract_section(clean, "done")
    problems = _extract_section(clean, "problems")
    plan = _extract_section(clean, "plan")

    has_report = done is not None and len(done.strip()) > 0
    has_plan = plan is not None and len(plan.strip()) > 0
    format_valid = has_report and has_plan

    return {
        "done": done,
        "problems": problems,
        "plan": plan,
        "has_report": has_report,
        "has_plan": has_plan,
        "format_valid": format_valid,
        "raw_text": text,
    }


def _extract_section(text: str, section_name: str) -> Optional[str]:
    """
    Extract content under a section header like 'done:', 'problems:', 'plan:'.
    Returns the text between this header and the next header (or end of text).
    """
    # Match section header (case-insensitive), followed by content until next section or end
    pattern = rf"(?:^|\n)\s*{section_name}\s*:\s*(.*?)(?=\n\s*(?:done|problems|plan)\s*:|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        content = match.group(1).strip()
        return content if content else None
    return None
