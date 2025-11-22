from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import re

from PyPDF2 import PdfReader

app = FastAPI(title="Resume Analyzer Backend")

# === CORS (open; you can restrict to your Vercel domain later) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- simple stopword list for tokenization ---
STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "at",
    "with", "from", "by", "as", "is", "are", "was", "were", "be", "been",
    "this", "that", "these", "those", "it", "its", "i", "you", "we", "they",
    "he", "she", "them", "our", "your", "their", "my", "me",
    "etc", "about", "over", "under", "into", "out", "up", "down",
    "using", "use", "used"
}

# Basic dictionaries of skills – tweak for your tech stack
TECH_SKILLS = [
    "python", "java", "c++", "c", "javascript", "typescript",
    "react", "redux", "next.js",
    "node.js", "express", "fastapi", "django", "flask",
    "html", "css", "tailwind", "bootstrap",
    "mongodb", "mysql", "postgresql", "sql",
    "rest api", "restful api", "graphql",
    "git", "github", "docker",
    "aws", "azure", "gcp",
    "machine learning", "deep learning", "pandas", "numpy", "opencv",
]

SOFT_SKILLS = [
    "communication", "teamwork", "team collaboration", "leadership",
    "problem solving", "analytical", "time management",
    "adaptability", "self-motivated", "presentation skills",
    "stakeholder management", "critical thinking", "ownership",
]


# ---------------- Root & Health ---------------- #

@app.get("/", tags=["root"])
def read_root():
    return {
        "status": "ok",
        "message": "Resume Analyzer backend running. See /health and /docs",
    }


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "message": "backend healthy"}


# ---------------- Helpers ---------------- #

def extract_text_from_pdf(path: str) -> str:
    """Read all text from a PDF using PyPDF2."""
    try:
        reader = PdfReader(path)
        texts: List[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            texts.append(t)
        return "\n".join(texts)
    except Exception as e:
        print(f"PDF parse error: {e}")
        return ""


def tokenize(text: str) -> List[str]:
    # simple word tokenizer + lowercasing + stopword removal
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def jaccard_similarity(words1: List[str], words2: List[str]) -> float:
    s1 = set(words1)
    s2 = set(words2)
    if not s1 or not s2:
        return 0.0
    inter = len(s1 & s2)
    union = len(s1 | s2)
    return inter / union if union else 0.0


def find_skills(text: str, candidates: List[str]) -> List[str]:
    """Return list of skills from `candidates` that appear in `text`."""
    tlow = text.lower()
    found = []
    for s in candidates:
        if s.lower() in tlow:
            found.append(s)
    return sorted(set(found))


def get_job_skill_targets(job_desc: str) -> List[str]:
    """Skills that the JD is asking for (based on our dictionaries)."""
    if not job_desc:
        return []
    jlow = job_desc.lower()
    targets = []
    for s in TECH_SKILLS + SOFT_SKILLS:
        if s.lower() in jlow:
            targets.append(s)
    return sorted(set(targets))


def compute_ats_score(
    job_targets: List[str],
    missing_skills: List[str],
    resume_tokens: List[str],
    jd_tokens: List[str],
    resume_skills_count: int,
    resume_length: int,
) -> int:
    """
    Cheap ATS-style score:
    - combine word overlap between resume & JD (jaccard)
    - plus coverage of job-required skills
    """
    similarity = jaccard_similarity(resume_tokens, jd_tokens)
    sim_pct = similarity * 100.0

    if job_targets:
        matched = len(job_targets) - len(missing_skills)
        total = max(1, len(job_targets))
        coverage_ratio = max(0.0, matched / total)
        coverage_pct = coverage_ratio * 100.0

        # 60% weight to JD–resume overlap, 40% to skill coverage
        raw = 0.6 * sim_pct + 0.4 * coverage_pct

        # small bonus for richer resumes
        if resume_skills_count > 10:
            raw += 5
        elif resume_skills_count > 5:
            raw += 2
        return max(10, min(99, int(raw)))

    # no JD: just based on resume richness
    if resume_length < 800:
        base = 55
    elif resume_length < 1500:
        base = 65
    else:
        base = 75

    if resume_skills_count > 12:
        base += 10
    elif resume_skills_count > 7:
        base += 5

    return max(40, min(95, base))


def group_missing_skills(missing: List[str]) -> dict:
    """
    Group missing skills into rough categories to craft better suggestions.
    """
    groups = {
        "backend": [],
        "frontend": [],
        "data": [],
        "cloud": [],
        "general": [],
    }
    for s in missing:
        sl = s.lower()
        if any(k in sl for k in ["node", "django", "fastapi", "flask", "api"]):
            groups["backend"].append(s)
        elif any(k in sl for k in ["react", "css", "html", "bootstrap", "tailwind", "frontend", "ui"]):
            groups["frontend"].append(s)
        elif any(k in sl for k in ["machine learning", "deep learning", "pandas", "numpy", "data"]):
            groups["data"].append(s)
        elif any(k in sl for k in ["aws", "azure", "gcp", "cloud", "docker"]):
            groups["cloud"].append(s)
        else:
            groups["general"].append(s)
    return groups


def build_suggestions(
    job_desc: str,
    job_targets: List[str],
    missing_skills: List[str],
    tech_found: List[str],
    soft_found: List[str],
    resume_length: int,
    similarity: float,
) -> List[str]:
    suggestions: List[str] = []

    # --- 1. JD vs Resume – missing skills, grouped ---
    if job_desc:
        if missing_skills:
            groups = group_missing_skills(missing_skills)
            if groups["backend"]:
                suggestions.append(
                    "Strengthen your backend profile by adding bullets that show hands-on work with: "
                    + ", ".join(groups["backend"]) +
                    ". Mention specific APIs, endpoints, or performance improvements you delivered."
                )
            if groups["frontend"]:
                suggestions.append(
                    "Highlight frontend work using: "
                    + ", ".join(groups["frontend"]) +
                    ". Add a project or experience bullet where you built responsive UI and explain your role clearly."
                )
            if groups["data"]:
                suggestions.append(
                    "The job expects data/ML exposure. Add a short section or project that demonstrates using: "
                    + ", ".join(groups["data"]) +
                    " with a clear problem, dataset and result."
                )
            if groups["cloud"]:
                suggestions.append(
                    "Show some cloud/devops experience involving: "
                    + ", ".join(groups["cloud"]) +
                    ". Briefly mention deployments, CI/CD, or infrastructure you worked on."
                )
            if groups["general"]:
                suggestions.append(
                    "These skills are important in the job description but not obvious in your resume: "
                    + ", ".join(groups["general"]) +
                    ". Try to connect them to a past project or add them in your Skills section with context."
                )
        else:
            suggestions.append(
                "Your resume covers almost all key skills from the job description. Make sure the most relevant ones are visible in the top third of the first page."
            )

        # similarity-based wording suggestion
        if similarity < 0.2:
            suggestions.append(
                "Rewrite some bullets to mirror the wording from the job description (same skill names and responsibilities) so ATS keyword matching is stronger."
            )
        elif similarity < 0.4:
            suggestions.append(
                "You have partial overlap with the job description. Rephrase a few bullets to include exact phrases from the JD, especially for the most important skills."
            )
        else:
            suggestions.append(
                "Your resume already matches the JD wording fairly well. Focus on tightening bullets to show measurable impact and results (numbers, percentages, time saved)."
            )
    else:
        suggestions.append(
            "Paste a specific job description next time so the analyzer can target missing skills and match score for that role."
        )

    # --- 2. Technical skills coverage ---
    if len(tech_found) < 4:
        suggestions.append(
            "Create a clear 'Technical Skills' section where you list languages, frameworks, databases and tools. Recruiters should understand your tech stack in 5 seconds."
        )
    else:
        suggestions.append(
            "Group your technical skills into categories (Languages, Frameworks, Databases, Tools) and keep only the ones you are comfortable being interviewed on."
        )

    # --- 3. Soft skills visibility ---
    if not soft_found:
        suggestions.append(
            "Mention 2–3 strong soft skills like communication, teamwork or problem solving, and tie them to concrete situations in your project or internship bullets."
        )
    elif len(soft_found) < 3:
        suggestions.append(
            "You hint at some soft skills, but you can be more explicit. For example: 'Collaborated with a 3-person team to …', 'Communicated results to stakeholders …'."
        )

    # --- 4. Resume length / density ---
    if resume_length < 600:
        suggestions.append(
            "Your resume looks quite short. Add more detail for each project: tech stack, your exact responsibilities, and one line of measurable outcome."
        )
    elif resume_length > 2600:
        suggestions.append(
            "Your resume might be too long. Remove older or less relevant items and keep 4–6 strong bullets per role focusing on impact, not tasks."
        )

    # keep suggestions list not too huge
    if len(suggestions) > 8:
        suggestions = suggestions[:8]

    return suggestions


# ---------------- Upload Endpoint ---------------- #

@app.post("/upload", tags=["upload"])
async def upload_resume(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
):
    """
    Upload a resume PDF, save it, and return a pdf_id that the frontend
    can use later when calling /analyze.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        content = await file.read()
        size = len(content)

        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as f:
            f.write(content)

        pdf_id = file.filename

        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "pdf_id": pdf_id,
                "filename": file.filename,
                "stored_path": save_path,
                "size_bytes": size,
                "job_description": job_description or "",
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)},
        )


# ---------------- Analyze Endpoint ---------------- #

class AnalyzeRequest(BaseModel):
    pdf_id: Optional[str] = None
    file_path: Optional[str] = None  # kept for future if needed
    job_description: Optional[str] = None
    force: Optional[bool] = False


@app.post("/analyze", tags=["analyze"])
async def analyze_resume(req: AnalyzeRequest):
    """
    Offline ATS-style analysis: compare resume vs job description, detect
    skills, compute a match score, and generate suggestions.
    """
    if not req.pdf_id:
        raise HTTPException(status_code=400, detail="pdf_id is required.")

    pdf_path = os.path.join(UPLOAD_DIR, req.pdf_id)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found on server.")

    # 1. Extract text from resume
    resume_text = extract_text_from_pdf(pdf_path)
    if not resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the PDF. Make sure it's not just images.",
        )

    job_desc = req.job_description or ""

    # 2. Tokenize
    resume_tokens = tokenize(resume_text)
    jd_tokens = tokenize(job_desc) if job_desc else []

    # 3. Detect skills in resume
    tech_found = find_skills(resume_text, TECH_SKILLS)
    soft_found = find_skills(resume_text, SOFT_SKILLS)

    # 4. Determine which skills JD is asking for & missing skills
    job_targets = get_job_skill_targets(job_desc)
    missing_skills_job = [
        s for s in job_targets if s not in tech_found and s not in soft_found
    ]

    # 5. Similarity & ATS score
    similarity = jaccard_similarity(resume_tokens, jd_tokens)
    ats_score = compute_ats_score(
        job_targets=job_targets,
        missing_skills=missing_skills_job,
        resume_tokens=resume_tokens,
        jd_tokens=jd_tokens,
        resume_skills_count=len(tech_found) + len(soft_found),
        resume_length=len(resume_text),
    )

    # 6. Suggestions
    suggestions = build_suggestions(
        job_desc=job_desc,
        job_targets=job_targets,
        missing_skills=missing_skills_job,
        tech_found=tech_found,
        soft_found=soft_found,
        resume_length=len(resume_text),
        similarity=similarity,
    )

    preview = resume_text[:2000]

    return {
        "analysis": {
            "ats_score": ats_score,
            "missing_skills_job": missing_skills_job,
            "suggestions": suggestions,
            "skills_found": tech_found,
            "soft_skills_found": soft_found,
            "raw_text_preview": preview,
        }
    }
