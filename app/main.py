from pathlib import Path
from app.services.matcher import match_candidate_to_job
from fastapi import FastAPI, File, UploadFile, HTTPException
from app.services.candidate_extractor import extract_candidate_profile
from app.services.resume_parser import extract_text_from_pdf
from dotenv import load_dotenv
from app.services.job_analyzer import analyze_job_description
load_dotenv()

app = FastAPI(
    title="AI Career Preparation Agent",
    description="Backend for resume and job preparation analysis",
    version="1.0.0"
)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "AI Career Preparation Agent API is running"
    }


@app.post("/resume/upload")
async def upload_resume(file: UploadFile = File(...)):

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported."
        )

    file_path = UPLOAD_DIR / file.filename

    contents = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    extracted_text = extract_text_from_pdf(str(file_path))
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
    if resume.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF resumes are supported."
        )

    if not job_description.strip():
        raise HTTPException(
            status_code=400,
            detail="Job description cannot be empty."
        )

    # Save resume
    file_path = UPLOAD_DIR / resume.filename

    contents = await resume.read()

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    # Extract resume text
    resume_text = extract_text_from_pdf(str(file_path))

    # Convert resume → CandidateProfile
    candidate_profile = extract_candidate_profile(resume_text)
    print("\n===== CANDIDATE SKILLS =====")
    print(candidate_profile.model_dump_json(indent=2))
    # Convert JD → JobProfile
    job_profile = analyze_job_description(job_description)

    # Match candidate against job
    match_report = match_candidate_to_job(
        candidate_profile,
        job_profile
    )
    
    match_report = match_candidate_to_job(
    candidate_profile,
    job_profile
)
    print("\n===== MATCH REPORT =====")
    print(match_report.model_dump_json(indent=2))
    return {
        "candidate_profile": candidate_profile.model_dump(),
        "job_profile": job_profile.model_dump(),
        "match_report": match_report.model_dump()
    }