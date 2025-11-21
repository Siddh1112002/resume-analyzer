# backend/app/suggestions_plugin.py
# -*- coding: utf-8 -*-
def _pluralize(word, n):
    return word if n == 1 else word + "s"

def build_suggestions(skills_found, missing_skills_job, strengths, doc_text):
    suggestions = []

    if missing_skills_job:
        first_missing = missing_skills_job[:8]
        suggestions.append(
            "Add or emphasize these skill{} in your Skills / Projects / Experience sections: {}."
            .format("" if len(first_missing)==1 else "s", ", ".join(first_missing))
        )
        suggestions.append(
            "For each added skill, add 1 short bullet describing where/how you used it (project, duration, impact). E.g., 'Built X with Y, improved performance by 30%.'"
        )

    if strengths:
        top_strengths = strengths[:6]
        suggestions.append(
            "Highlight strengths ({}). Put these in a 'Key Projects' or 'Selected Experience' section with 1–2 outcome bullets each."
            .format(", ".join(top_strengths))
        )

    lower = (doc_text or "").lower()
    if not any(k in lower for k in ("%", "reduc", "improv", "increas", "achiev", "handled", "reduced", "boosted", "saved")):
        suggestions.append(
            "Add 1–3 quantified achievements (metrics or outcomes). Example: 'Reduced page load time by 30%' or 'Handled 10k requests/day'."
        )

    soft_candidates = ["communication", "teamwork", "problem solving", "time management", "leadership", "collaboration"]
    found_soft = [s for s in soft_candidates if s in (skills_found or []) or s in (strengths or [])]
    if not found_soft:
        suggestions.append(
            "Add 1–2 soft skills with short examples. E.g., 'led a 3-person team to deliver feature X' or 'collaborated with designers to reduce UX friction'."
        )
    else:
        suggestions.append(
            "For soft skills ({}), add a one-line example each in Experience or Projects showing how you demonstrated them."
            .format(", ".join(found_soft))
        )

    suggestions.append(
        "Polish bullet wording: Use 'Action + Task + Result' (e.g., 'Built X using Y, improving Z by 20%'). Keep bullets concise (1 line)."
    )
    suggestions.append(
        "If you have space, add a 'Tools & Tech' mini-list (1-line) and link to 1–2 code samples or live demos."
    )

    seen = set()
    out = []
    for s in suggestions:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out
