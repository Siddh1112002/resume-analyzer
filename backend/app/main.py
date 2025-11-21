# C:\projects\resume-analyzer\backend\app\main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import os

app = FastAPI(title="Resume Analyzer Backend")

# === CORS settings ===
# Replace the RENDER_BACKEND_URL value below with your actual Render URL if needed.
# We'll default to env var RENDER_BACKEND_URL or common dev hosts.
RENDER_BACKEND_URL = os.getenv("RENDER_BACKEND_URL", "https://resume-analyzer-xc2a.onrender.com")

origins = [
    "http://localhost:5173",       # local dev frontend
    "http://127.0.0.1:5173",
    RENDER_BACKEND_URL,            # deployed frontend domain (you can change to your actual Vercel URL)
    # add any additional frontends here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,    # production: list explicit origins; for debug you may use ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Helpful root & health endpoints ===
@app.get("/", tags=["root"])
def read_root():
    return {"status": "ok", "message": "Resume Analyzer backend running. See /health and /docs"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "message": "backend healthy"}

# === Upload endpoint (example)
# Make sure your frontend FormData field name is `file` and optional `job_description`.
@app.post("/upload", tags=["upload"])
async def upload_resume(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
):
    """
    Example upload endpoint. Adjust body to match your existing analyzer logic.
    This accepts a multipart upload with field 'file' and optional 'job_description'.
    """
    try:
        # basic example: read a few bytes to ensure upload works
        content = await file.read()
        size = len(content)

        # TODO: replace the following with your actual analyzer processing
        # For now return success and sizes so frontend can confirm backend is receiving file.
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "filename": file.filename,
                "size_bytes": size,
                "job_description": job_description or "",
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})
