from .suggestions_plugin import build_suggestions
import os, re
from typing import Optional, List, Dict
from PyPDF2 import PdfReader

SKILLS_LIST = [
    "python","java","c","c++","javascript","react","node","express","mongodb",
    "sql","mysql","html","css","git","docker","aws","pandas","numpy",
    "tensorflow","scikit-learn","rest","api","typescript","tailwind","redux"
]

SOFT_SKILLS = [
    "communication","teamwork","problem solving","leadership","time management",
    "management","collaboration","adaptability"
]

def extract_text_from_pdf(path: str) -> str:
    if not os.path.exists(path):
        raise RuntimeError(f"PDF path not found: {path}")
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        t = p.extract_text()
        if t:
            pages.append(t)
    return "\n".join(pages)

def _match_words_from_list(text: str, words: List[str]) -> List[str]:
    text_l = (text or "").lower()
    found = []
    for w in words:
        if re.search(r"\b" + re.escape(w.lower()) + r"\b", text_l):
            found.append(w)
    return sorted(set(found))

def analyze_resume(pdf_path: Optional[str] = None, pdf_text: Optional[str] = None, job_description: str = "") -> Dict:
    if pdf_text is None:
        if not pdf_path:
            raise RuntimeError("analyze_resume: either pdf_path or pdf_text must be provided")
        text = extract_text_from_pdf(pdf_path)
    else:
        text = pdf_text

    doc_text = text or ""
    skills_found = _match_words_from_list(doc_text, SKILLS_LIST)
    soft_found = _match_words_from_list(doc_text, SOFT_SKILLS)
    jd_required = _match_words_from_list(job_description or "", SKILLS_LIST)

    if jd_required:
        matched_required = set(skills_found) & set(jd_required)
        ats_score = int(round(100.0 * len(matched_required) / max(1, len(jd_required))))
    else:
        ats_score = int(round(100.0 * len(skills_found) / max(1, len(SKILLS_LIST))))

    missing_skills = sorted([s for s in jd_required if s not in skills_found])

    strengths = skills_found[:6]

    try:
        suggestions = build_suggestions(skills_found, missing_skills, strengths, doc_text)
    except Exception as e:
        suggestions = [f"Could not generate suggestions: {e}"]

    if not skills_found:
        suggestions.append("No technical skills detected. Add a Skills or Projects section listing tech stacks.")
    if not soft_found:
        suggestions.append("Add 1-2 soft skills with short examples (teamwork, communication, problem solving).")

    result = {
        "ats_score": int(max(0, min(100, ats_score))),
        "skills_found": skills_found,
        "soft_skills_found": soft_found,
        "missing_skills_job": missing_skills,
        "strengths": strengths,
        "suggestions": suggestions,
        "raw_text_preview": doc_text[:1000]
    }
    return result
