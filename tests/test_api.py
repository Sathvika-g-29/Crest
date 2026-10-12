
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
def test_match_rejects_empty_job_description(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "resume.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Python developer")
        document.save(pdf_path)

    with pdf_path.open("rb") as resume:
        response = client.post(
            "/match",
            data={"job_description": "   "},
            files={
                "resume": (
                    "resume.pdf",
                    resume,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Job description cannot be empty."
    
def test_match_rejects_invalid_pdf():
    response = client.post(
        "/match",
        data={"job_description": "Python developer required"},
        files={
            "resume": (
                "resume.pdf",
                b"This is not a real PDF",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400

def test_resume_upload_with_valid_pdf(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "resume.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Python developer with FastAPI experience",
        )
        document.save(pdf_path)

    with pdf_path.open("rb") as resume:
        response = client.post(
            "/resume/upload",
            files={
                "file": (
                    "resume.pdf",
                    resume,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200
    assert "candidate_profile" in response.json()

def test_match_with_valid_resume_and_job_description(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "resume.pdf"

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Python developer. Built REST APIs using FastAPI. "
            "Created a retrieval augmented generation project.",
        )
        document.save(pdf_path)

    with pdf_path.open("rb") as resume:
        response = client.post(
            "/match",
            data={
                "job_description": (
                    "Seeking a Python developer with FastAPI "
                    "and REST API development experience."
                )
            },
            files={
                "resume": (
                    "resume.pdf",
                    resume,
                    "application/pdf",
                )
            },
        )
    print("Response:", response.status_code, response.text)
    assert response.status_code == 200
    result = response.json()
    assert "candidate_profile" in result
    assert "job_profile" in result
    assert "match_report" in result

def test_submit_answer_rejects_empty_question():
    response = client.post(
        "/interview/submit-answer",
        params={
            "question": "   ",
            "candidate_answer": "Conditional edges select the next node.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question cannot be empty."

def test_submit_answer_rejects_empty_candidate_answer():
    response = client.post(
        "/interview/submit-answer",
        params={
            "question": "How do conditional edges work in LangGraph?",
            "candidate_answer": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Candidate answer cannot be empty."
