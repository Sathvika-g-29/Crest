
import json
import sqlite3
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, File, UploadFile, HTTPException

from app.services.interview_workflow import interview_workflow
from app.services.matcher import match_candidate_to_job
from app.services.candidate_extractor import extract_candidate_profile
from app.services.resume_parser import extract_text_from_pdf
from app.services.job_analyzer import analyze_job_description
from app.models.interview import InterviewQuestion
from app.services.interview_generator import generate_interview_question
from app.services.answer_evaluator import evaluate_answer
from app.services.followup_generator import generate_followup_question


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="AI Career Preparation Agent",
    description="Backend for resume and job preparation analysis",
    version="1.0.0",
)


# --------------------------------------------------
# SQLite interview-session storage
# --------------------------------------------------

DB_PATH = "interviews.db"


def init_interview_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                interview_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL
            )
        """)


def save_interview(interview_id: str, state: dict):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO interviews
            (interview_id, state_json)
            VALUES (?, ?)
            """,
            (interview_id, json.dumps(state)),
        )


def load_interview(interview_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT state_json FROM interviews WHERE interview_id = ?",
            (interview_id,),
        ).fetchone()

    return json.loads(row[0]) if row else None


init_interview_db()


# --------------------------------------------------
# Common AI error handling
# --------------------------------------------------

def invoke_interview_workflow(state: dict):
    try:
        return interview_workflow.invoke(state)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI service is temporarily unavailable. "
                "Please retry shortly. Your previous interview "
                "state has been preserved."
            ),
        ) from exc


# --------------------------------------------------
# Resume upload configuration
# --------------------------------------------------

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_RESUME_SIZE = 5 * 1024 * 1024


async def save_resume(file: UploadFile) -> Path:
    """Validate and save an uploaded PDF using a safe filename."""

    if file.content_type != "application/pdf":
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported.",
        )

    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}.pdf"
    total_size = 0

    try:
        with file_path.open("xb") as buffer:
            while True:
                chunk = await file.read(64 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_RESUME_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Resume exceeds the 5 MB file-size limit.",
                    )

                buffer.write(chunk)

        with file_path.open("rb") as saved_file:
            if saved_file.read(5) != b"%PDF-":
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file is not a valid PDF.",
                )

        return file_path

    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "AI Career Preparation Agent API is running"
    }


# --------------------------------------------------
# Resume upload
# --------------------------------------------------

@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    file_path = await save_resume(file)

    try:
        extracted_text = extract_text_from_pdf(str(file_path))
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    candidate_profile = extract_candidate_profile(extracted_text)

    return {
        "filename": file.filename,
        "candidate_profile": candidate_profile.model_dump(),
    }


# --------------------------------------------------
# Job description analysis
# --------------------------------------------------

@app.post("/job/analyze")
async def analyze_job(job_description: str):
    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty.",
        )

    job_profile = analyze_job_description(job_description)

    return {
        "job_profile": job_profile.model_dump(),
    }


# --------------------------------------------------
# Resume-to-job matching
# --------------------------------------------------

@app.post("/match")
async def match_resume_to_job(
    resume: UploadFile = File(...),
    job_description: str = Form(""),
):
    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty.",
        )

    file_path = await save_resume(resume)

    try:
        resume_text = extract_text_from_pdf(str(file_path))
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    candidate_profile = extract_candidate_profile(resume_text)
    job_profile = analyze_job_description(job_description)

    match_report = match_candidate_to_job(
        candidate_profile,
        job_profile,
    )

    return {
        "candidate_profile": candidate_profile.model_dump(),
        "job_profile": job_profile.model_dump(),
        "match_report": match_report.model_dump(),
    }


# --------------------------------------------------
# Standalone interview-question generation
# --------------------------------------------------

@app.post("/interview-question")
async def create_interview_question(
    skill: str,
    resume_evidence: str,
):
    if not skill.strip() or not resume_evidence.strip():
        raise HTTPException(
            status_code=400,
            detail="Skill and resume evidence are required.",
        )

    question = generate_interview_question(
        skill=skill,
        resume_evidence=resume_evidence,
    )

    return InterviewQuestion(
        skill=skill,
        question=question,
        resume_evidence=resume_evidence,
    ).model_dump()


# --------------------------------------------------
# Standalone answer evaluation
# --------------------------------------------------

@app.post("/evaluate-answer")
async def evaluate_interview_answer(
    question: str,
    candidate_answer: str,
):
    if not question.strip() or not candidate_answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Question and candidate answer are required.",
        )

    try:
        evaluation = evaluate_answer(
            question=question,
            candidate_answer=candidate_answer,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unavailable. Please retry.",
        ) from exc

    return evaluation.model_dump()


# --------------------------------------------------
# Standalone follow-up-question generation
# --------------------------------------------------

@app.post("/followup-question")
async def create_followup_question(
    original_question: str,
    candidate_answer: str,
    knowledge_gaps: list[str],
):
    if not original_question.strip() or not candidate_answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Original question and candidate answer are required.",
        )

    if not knowledge_gaps:
        raise HTTPException(
            status_code=400,
            detail="At least one knowledge gap is required.",
        )

    question = generate_followup_question(
        original_question=original_question,
        candidate_answer=candidate_answer,
        knowledge_gaps=knowledge_gaps,
    )

    return {
        "original_question": original_question,
        "followup_question": question,
        "knowledge_gaps": knowledge_gaps,
    }


# --------------------------------------------------
# Start a stateful interview
# --------------------------------------------------

@app.post("/interview/start")
async def start_interview(
    skill: str,
    resume_evidence: str,
):
    if not skill.strip() or not resume_evidence.strip():
        raise HTTPException(
            status_code=400,
            detail="Skill and resume evidence are required.",
        )

    interview_id = str(uuid.uuid4())

    initial_state = {
        "skill": skill,
        "resume_evidence": resume_evidence,
        "current_question": "",
        "candidate_answer": "",
        "correctness_score": 0.0,
        "knowledge_gaps": [],
        "interview_history": [],
        "followup_question": "",
        "next_action": "answer",
        "interview_status": "in_progress",
    }

    result = invoke_interview_workflow(initial_state)

    save_interview(interview_id, result)

    return {
        "interview_id": interview_id,
        "first_question": result["current_question"],
        "interview_status": result["interview_status"],
    }


# --------------------------------------------------
# Submit an answer and continue the same interview
# --------------------------------------------------

@app.post("/interview/submit-answer")
async def submit_interview_answer(
    interview_id: str,
    candidate_answer: str,
):
    if not candidate_answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Candidate answer cannot be empty.",
        )

    state = load_interview(interview_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found.",
        )

    if state.get("interview_status") == "completed":
        raise HTTPException(
            status_code=400,
            detail="This interview has already ended.",
        )

    state["candidate_answer"] = candidate_answer

    # The database is updated only after successful workflow execution.
    result = invoke_interview_workflow(state)

    history = result.get("interview_history", [])

    if not history:
        raise HTTPException(
            status_code=500,
            detail="The workflow did not record the submitted answer.",
        )

    save_interview(interview_id, result)

    latest = history[-1]

    return {
        "interview_id": interview_id,
        "evaluation": {
            "correctness_score": latest["score"],
            "knowledge_gaps": latest["knowledge_gaps"],
            "feedback": latest["feedback"],
        },
        "next_question": result.get("current_question"),
        "next_action": result["next_action"],
        "interview_status": result["interview_status"],
        "total_answers": len(history),
    }


# --------------------------------------------------
# Explicitly end an interview
# --------------------------------------------------

@app.post("/interview/end")
async def end_interview(interview_id: str):
    state = load_interview(interview_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found.",
        )

    if state.get("interview_status") != "completed":
        state["interview_status"] = "completed"
        state["next_action"] = "complete"
        save_interview(interview_id, state)

    return {
        "interview_id": interview_id,
        "interview_status": "completed",
        "total_answers": len(state.get("interview_history", [])),
        "interview_history": state.get("interview_history", []),
    }
