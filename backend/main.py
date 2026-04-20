import json
import os
from typing import Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from .generate import generate_emails
from .notion_client import save_sent_email
from .pdf_parser import extract_text_from_pdf
from .research import research_person

app = FastAPI(title="Cold Email Generator")

origins = [
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:8000",
    "http://127.0.0.1:5500",  # Live Server default
    "null",                   # file:// origin when opening HTML directly
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /api/health ──────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    provider = "claude" if os.getenv("ANTHROPIC_API_KEY") else (
        "groq" if os.getenv("GROQ_API_KEY") else "none"
    )
    return {
        "status": "ok",
        "provider": provider,
        "notion": bool(os.getenv("NOTION_API_KEY")),
    }


# ── /api/parse-pdf ───────────────────────────────────────────────────

@app.post("/api/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    try:
        text = extract_text_from_pdf(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse PDF: {e}")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from this PDF")
    return {"text": text}


# ── /api/research ────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    name: str
    role: str
    company: str
    resume_text: str = ""


@app.post("/api/research")
async def research(req: ResearchRequest):
    if not req.name or not req.company:
        raise HTTPException(status_code=400, detail="name and company are required")
    try:
        result = await research_person(
            name=req.name,
            role=req.role,
            company=req.company,
            resume_text=req.resume_text,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {e}")
    return result


# ── /api/generate ────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    resume_text: str
    job_description: str
    person_name: str
    person_role: str
    company: str
    tones: List[str] = ["Formal", "Conversational", "Story Driven", "Data Driven"]
    hooks: Dict = {}
    notes: str = ""
    user_name: str = "the applicant"
    context: str = ""
    contact_method: str = "email"


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not req.job_description.strip():
        raise HTTPException(status_code=400, detail="job_description is required")
    try:
        result = await generate_emails(
            resume_text=req.resume_text,
            job_description=req.job_description,
            person_name=req.person_name,
            person_role=req.person_role,
            company=req.company,
            tones=req.tones,
            hooks=req.hooks,
            notes=req.notes,
            user_name=req.user_name,
            context=req.context,
            contact_method=req.contact_method,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")
    return result


# ── /api/notion/save ─────────────────────────────────────────────────

class NotionSaveRequest(BaseModel):
    person: str
    company: str
    role: str
    email_address: str = ""
    linkedin_url: str = ""
    job_link: str = ""


@app.post("/api/notion/save")
async def notion_save(req: NotionSaveRequest):
    try:
        ok = await save_sent_email(
            person=req.person,
            company=req.company,
            role=req.role,
            email_address=req.email_address,
            linkedin_url=req.linkedin_url,
            job_link=req.job_link,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Notion save failed: {e}")
    if not ok:
        raise HTTPException(status_code=502, detail="Notion returned a non-200 response")
    return {"saved": True}
