# C:\projects\resume-analyzer\backend\app\main.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os

app = FastAPI(title="Resume Analyzer Backend")

# === CORS (for now: open to all so frontend can connect easily) ===
# After everything works, you can restrict this to your Vercel domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # allow all origins (Vercel, localhost, etc.)
    allow_credentials=False,   # must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Upload directory ===
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# === Root & health endpoints ===
@app.get("/", tags=["root"])
def read_root():
    return {"status": "ok", "message": "Resume Analyzer backend running. See /health and /docs"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "message": "backend healthy"}


# === Upload endpoint ===
# Frontend sends: FormData with "file" and optional "job_description".
@app.post("/upload", tags=["upload"])
async def upload_resume(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
):
    """
    Upload a resume PDF, save it, and return a pdf_id the frontend can use later.
    """
    try:
        # Read file content
        content = await file.read()
        size = len(content)

        # Save to uploads folder
        save_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(save_path, "wb") as f:
            f.write(content)

        # Simple pdf_id = filename (you can change later if you want)
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
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})


# === Analyze endpoint ===
# Frontend sends JSON: { pdf_id, job_description, force }
class AnalyzeRequest(BaseModel):
    pdf_id: Optional[str] = None
    file_path: Optional[str] = None  # kept for future if needed
    job_description: Optional[str] = None
    force: Optional[bool] = False


@app.post("/analyze", tags=["analyze"])
async def analyze_resume(req: AnalyzeRequest):
    """
    Dummy analysis endpoint so UI works end-to-end.
    Replace this with real AI / PDF parsing logic later.
    """

    # In a real implementation, you would:
    # - locate the uploaded file by pdf_id in UPLOAD_DIR
    # - extract text from the PDF
    # - run your AI / scoring logic
    # For now we just send back some fake but realistic data.
    fake_ats_score = 82

    return {
        "analysis": {
            "ats_score": fake_ats_score,
            "missing_skills_job": ["Docker", "Kubernetes", "CI/CD"],
            "suggestions": [
                "Add 2–3 bullet points with measurable impact for each major project.",
                "Mention any experience with Docker, Kubernetes or deployment pipelines.",
                "Include a short 'Summary' section tailored to the target job description.",
            ],
            "skills_found": [
                "Python",
                "FastAPI",
                "React",
                "Node.js",
                "MongoDB",
                "SQL",
                "Git",
            ],
            "soft_skills_found": [
                "Team Collaboration",
                "Communication",
                "Problem Solving",
                "Time Management",
            ],
            "raw_text_preview": (
                "This is a placeholder preview of your resume text. "
                "Once you plug in real parsing, this will show the first part of the extracted content..."
            ),
        }
    }
