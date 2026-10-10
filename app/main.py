
from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException

import uuid

from fastapi import HTTPException, UploadFile

from app.services.matcher import match_candidate_to_job
from app.services.candidate_extractor import extract_candidate_profile
from app.services.resume_parser import extract_text_from_pdf
from app.services.job_analyzer import analyze_job_description
from app.models.interview import InterviewQuestion
from app.services.interview_generator import generate_interview_question
from app.services.answer_evaluator import evaluate_answer
from app.services.followup_generator import generate_followup_question
app = FastAPI(
    title="AI Career Preparation Agent",
    description="Backend for resume and job preparation analysis",
    version="1.0.0"
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB


async def save_resume(file: UploadFile) -> Path:
    """Validate and save an uploaded PDF using a safe filename."""

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported."
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
                        detail="Resume exceeds the 5 MB file-size limit."
                    )

                buffer.write(chunk)

        # Check that the file actually contains a PDF.
        with file_path.open("rb") as saved_file:
            if saved_file.read(5) != b"%PDF-":
                raise HTTPException(
                    status_code=400,
                    detail="The uploaded file is not a valid PDF."
                )

        return file_path

    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

@app.get("/")
def root():
    return {
        "message": "AI Career Preparation Agent API is running"
    }



@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    file_path = await save_resume(file)

    try:
        extracted_text = extract_text_from_pdf(str(file_path))
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    candidate_profile = extract_candidate_profile(extracted_text)

    return {
        "filename": file.filename,
        "candidate_profile": candidate_profile.model_dump()
    }

@app.post("/job/analyze")
async def analyze_job(job_description: str):

    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    job_profile = analyze_job_description(job_description)
    print("\n===== JOB PROFILE =====")
    print(job_profile.model_dump_json(indent=2))

    return {
        "job_profile": job_profile.model_dump()
    }

@app.post("/match")
async def match_resume_to_job(
    resume: UploadFile = File(...),
    job_description: str = ""
):
    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    file_path = await save_resume(resume)

    try:
        resume_text = extract_text_from_pdf(str(file_path))
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    candidate_profile = extract_candidate_profile(resume_text)
    job_profile = analyze_job_description(job_description)

    match_report = match_candidate_to_job(
        candidate_profile,
        job_profile
    )

    return {
        "candidate_profile": candidate_profile.model_dump(),
        "job_profile": job_profile.model_dump(),
        "match_report": match_report.model_dump()
    }

@app.post("/interview-question")
async def create_interview_question(
    skill: str,
    resume_evidence: str
):
    if not skill.strip():
        raise HTTPException(
            status_code=400,
            detail="Skill cannot be empty."
        )

    if not resume_evidence.strip():
        raise HTTPException(
            status_code=400,
            detail="Resume evidence cannot be empty."
        )

    question = generate_interview_question(
        skill=skill,
        resume_evidence=resume_evidence
    )

    return InterviewQuestion(
        skill=skill,
        question=question,
        resume_evidence=resume_evidence
    ).model_dump()

@app.post("/evaluate-answer")
async def evaluate_interview_answer(
    question: str,
    candidate_answer: str
):
    if not question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    if not candidate_answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Candidate answer cannot be empty."
        )

    evaluation = evaluate_answer(
        question=question,
        candidate_answer=candidate_answer
    )

    return evaluation.model_dump()

@app.post("/followup-question")
async def create_followup_question(
    original_question: str,
    candidate_answer: str,
    knowledge_gaps: list[str]
):
    if not original_question.strip():
        raise HTTPException(
            status_code=400,
            detail="Original question cannot be empty."
        )

    if not candidate_answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Candidate answer cannot be empty."
        )

    if not knowledge_gaps:
        raise HTTPException(
            status_code=400,
            detail="At least one knowledge gap is required."
        )

    question = generate_followup_question(
        original_question=original_question,
        candidate_answer=candidate_answer,
        knowledge_gaps=knowledge_gaps
    )

    return {
        "original_question": original_question,
        "followup_question": question,
        "knowledge_gaps": knowledge_gaps
    }

@app.post("/interview/submit-answer")
async def submit_interview_answer(
    question: str,
    candidate_answer: str
):
    if not question.strip():
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    if not candidate_answer.strip():
        raise HTTPException(
            status_code=400,
            detail="Candidate answer cannot be empty."
        )

    # Step 1: Evaluate the candidate's answer
    evaluation = evaluate_answer(
        question=question,
        candidate_answer=candidate_answer
    )

    # Step 2: Generate a follow-up if gaps were identified
    followup_question = None

    if evaluation.knowledge_gaps:
        followup_question = generate_followup_question(
            original_question=question,
            candidate_answer=candidate_answer,
            knowledge_gaps=evaluation.knowledge_gaps
        )

    # Step 3: Return both results
    return {
        "evaluation": evaluation.model_dump(),
        "followup_question": followup_question
    }
