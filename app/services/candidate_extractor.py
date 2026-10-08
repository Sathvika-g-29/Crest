import os

from dotenv import load_dotenv
from google import genai

from app.models.candidate import CandidateProfile


load_dotenv()


def extract_candidate_profile(resume_text: str) -> CandidateProfile:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. Check your .env file."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are extracting structured information from a candidate's resume.

Use ONLY information explicitly present in the resume.
Do not invent skills, projects, experience, education, companies,
technologies, or other information.

Extract:

- candidate name
- technical and non-technical skills
- projects
- education
- work/internship experience

For each skill, return:

- name: the skill or technology name
- category: a concise category describing what kind of skill it is
- specificity: whether this is a specific technology, broader technology category, or concept
- evidence: where/how the resume demonstrates or mentions this skill

Use only these specificity values:

- specific_technology
- technology_category
- concept

Examples:

Python
category: programming_language
specificity: specific_technology

FastAPI
category: framework
specificity: specific_technology

ChromaDB
category: vector_database
specificity: specific_technology

REST API Integration
category: api
specificity: technology_category

machine learning
category: machine_learning
specificity: concept

RAG
category: concept
specificity: concept

Important:
- A named programming language, framework, library, database, or tool is usually a specific_technology.
- A broad group such as "REST APIs" or "vector databases" is usually a technology_category.
- A broad technical area such as "machine learning", "NLP", or "RAG" is usually a concept.
- Use only information explicitly present in the resume.
- Do not invent skills.
For projects, include the technologies explicitly mentioned.
For experience, summarize only what is supported by the resume.

Resume:
{resume_text}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": CandidateProfile,
        },
    )

    return CandidateProfile.model_validate_json(response.text)