
import os
from google import genai


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def generate_interview_question(
    skill: str,
    resume_evidence: str,
) -> str:

    prompt = f"""
    Generate one technical interview question for a job candidate.

    Skill to evaluate: {skill}

    Evidence from the candidate's resume:
    {resume_evidence}

    Instructions:
    - Ask one clear, specific technical question.
    - Connect the question to the resume evidence when possible.
    - Test the candidate's actual understanding, not just definitions.
    - Do not assume technologies or project details absent from the evidence.
    - Return only the question.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )

    return response.text.strip()
