from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import json

from PyPDF2 import PdfReader
from openai import OpenAI

app = FastAPI(title="Resume Analyzer Backend")

# --- CORS (open for dev/demo; you can restrict later) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# OpenAI client (reads OPENAI_API_KEY from env)
client = OpenAI()


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
        texts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            texts.append(t)
        return "\n".join(texts)
    except Exception as e:
        print(f"PDF parse error: {e}")
        return ""


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


# ---------------- Analyze Endpoint (AI) ---------------- #

class AnalyzeRequest(BaseModel):
    pdf_id: Optional[str] = None
    file_path: Optional[str] = None  # kept for future if needed
    job_description: Optional[str] = None
    force: Optional[bool] = False


@app.post("/analyze", tags=["analyze"])
async def analyze_resume(req: AnalyzeRequest):
    """
    Use GPT-4o-mini to analyze the resume text vs job description and
    return structured ATS-style analysis as JSON.
    """
    if not req.pdf_id:
        raise HTTPException(status_code=400, detail="pdf_id is required.")

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server.",
        )

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

    # 2. Build prompt for the model
    system_prompt = (
        "You are an expert ATS (Applicant Tracking System) resume analyzer. "
        "Given a candidate's resume text and a job description, you:\n"
        "- Identify the main technical skills and soft skills in the resume.\n"
        "- Compare them with the job description.\n"
        "- Estimate an ATS-style match score from 0 to 100.\n"
        "- List important skills from the job description that seem missing or weak.\n"
        "- Generate clear, practical suggestions to improve the resume for THIS job.\n\n"
        "You MUST return a single valid JSON object with this exact schema:\n"
        "{\n"
        '  "ats_score": number (0-100),\n'
        '  "skills_found": string[],           // technical skills inferred from resume\n'
        '  "soft_skills_found": string[],      // soft skills inferred from resume\n'
        '  "missing_skills_job": string[],     // skills clearly in JD but not in resume\n'
        '  "suggestions": string[]             // 4-8 bullet-style suggestions\n'
        "}\n"
        "Do not include any extra keys. Do not include explanations outside the JSON."
    )

    user_prompt = (
        "JOB DESCRIPTION:\n"
        "----------------\n"
        f"{job_desc or '[No job description provided]'}\n\n"
        "RESUME TEXT:\n"
        "------------\n"
        f"{resume_text}\n"
    )

    try:
        # 3. Call OpenAI with JSON response_format so we can parse easily
        #    (Chat Completions JSON mode). :contentReference[oaicite:1]{index=1}
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        raw_content = response.choices[0].message.content
        data = json.loads(raw_content)

    except Exception as e:
        # If anything goes wrong with the AI call or JSON parsing, log & fail gracefully
        print("OpenAI error:", e)
        raise HTTPException(
            status_code=500,
            detail="AI analysis failed. Check server logs for details.",
        )

    # 4. Normalize + add preview for the frontend PDF export
    ats_score = int(data.get("ats_score", 70))
    skills_found = data.get("skills_found", [])
    soft_skills_found = data.get("soft_skills_found", [])
    missing_skills_job = data.get("missing_skills_job", [])
    suggestions = data.get("suggestions", [])

    preview = resume_text[:2000]

    return {
        "analysis": {
            "ats_score": max(0, min(100, ats_score)),
            "missing_skills_job": missing_skills_job,
            "suggestions": suggestions,
            "skills_found": skills_found,
            "soft_skills_found": soft_skills_found,
            "raw_text_preview": preview,
        }
    }
