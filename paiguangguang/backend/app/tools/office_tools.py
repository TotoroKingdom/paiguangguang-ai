from __future__ import annotations

import re


OFFICE_STOPWORDS = {
    "about",
    "also",
    "an",
    "and",
    "are",
    "be",
    "can",
    "could",
    "did",
    "do",
    "does",
    "done",
    "for",
    "from",
    "get",
    "give",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "need",
    "of",
    "on",
    "or",
    "our",
    "should",
    "show",
    "tell",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "used",
    "using",
    "was",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
}


def _extract_keywords(prompt: str) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", prompt.lower()):
        if len(token) < 3 or token in OFFICE_STOPWORDS or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
    return keywords


def _title_from_keywords(keywords: list[str], fallback: str) -> str:
    if not keywords:
        return fallback
    words = [word.capitalize() for word in keywords[:4]]
    return " ".join(words)


def _append_suffix_once(base: str, suffix: str) -> str:
    normalized_base = base.strip()
    normalized_suffix = suffix.strip()
    if normalized_base.lower().endswith(normalized_suffix.lower()):
        return normalized_base
    return f"{normalized_base} {normalized_suffix}"


def summarize_data(prompt: str) -> dict[str, object]:
    keywords = _extract_keywords(prompt)
    subject = _title_from_keywords(keywords, "Office Summary")
    key_points = [
        f"Primary focus: {subject}.",
        f"Prompt keywords: {', '.join(keywords[:5]) if keywords else 'none identified'}.",
        "Turn the request into a concise office-ready artifact.",
    ]
    summary = (
        f"The workflow request focuses on {subject.lower()} and should be presented as a clean office artifact."
    )
    return {
        "subject": subject,
        "summary": summary,
        "key_points": key_points,
        "keywords": keywords,
    }


def generate_report(prompt: str, summary: dict[str, object]) -> dict[str, object]:
    subject = str(summary.get("subject") or _title_from_keywords(_extract_keywords(prompt), "Report"))
    title = _append_suffix_once(subject, "Report")
    report_sections = [
        {
            "heading": "Overview",
            "content": str(summary.get("summary") or prompt.strip()),
        },
        {
            "heading": "Key Findings",
            "content": "\n".join(f"- {point}" for point in summary.get("key_points", [])),
        },
        {
            "heading": "Recommended Actions",
            "content": "1. Share the draft with stakeholders.\n2. Review the requested changes.\n3. Finalize the office deliverable.",
        },
    ]
    report_body = "\n\n".join(
        f"## {section['heading']}\n{section['content']}" for section in report_sections
    )
    return {
        "title": title,
        "summary": str(summary.get("summary") or ""),
        "content": report_body,
        "sections": report_sections,
    }


def write_email(prompt: str, summary: dict[str, object]) -> dict[str, object]:
    subject = str(summary.get("subject") or _title_from_keywords(_extract_keywords(prompt), "Email"))
    email_subject = f"{subject}: next steps"
    key_points = summary.get("key_points", [])
    email_body = (
        "Hi team,\n\n"
        f"{summary.get('summary') or prompt.strip()}\n\n"
        "Key points:\n"
        + "\n".join(f"- {point}" for point in key_points)
        + "\n\nBest,\nPai Guangguang"
    )
    return {
        "recipient": "stakeholders",
        "subject": email_subject,
        "summary": str(summary.get("summary") or ""),
        "content": email_body,
    }
