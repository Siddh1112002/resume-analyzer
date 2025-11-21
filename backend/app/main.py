from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, shutil, uuid

from .analyzer import extract_text_from_pdf, analyze_resume

app = FastAPI(title="Resume Analyzer")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5175",
    "http://127.0.0.1:5175"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_DIR = os.path.join(BASE, "backend", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok", "message": "backend healthy"}

class AnalyzeRequest(BaseModel):
    pdf_id: str = None
    file_path: str = None
    job_description: str = ""
    force: bool = False

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename)[1]
    pdf_id = f"{str(uuid.uuid4())}_{file.filename}"
    save_path = os.path.join(UPLOAD_DIR, pdf_id)
    with open(save_path, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"pdf_id": pdf_id, "filename": file.filename, "path": save_path}

    @app.get("/")
def home():
    return {"status": "Backend is running!"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if req.pdf_id:
        path = os.path.join(UPLOAD_DIR, req.pdf_id)
    elif req.file_path:
        path = req.file_path
    else:
        raise HTTPException(status_code=400, detail="pdf_id or file_path required")

    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"file_path not found: {path}")

    try:
        result = analyze_resume(pdf_path=path, job_description=req.job_description or "")
        return {"pdf_ref": req.pdf_id or os.path.basename(path), "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
