import os

from dotenv import load_dotenv
from google import genai

from app.models.job import JobProfile


load_dotenv()


def analyze_job_description(job_description: str) -> JobProfile:

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is missing. Check your .env file."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are extracting structured information from a job description.

Use ONLY information explicitly present in the job description.
Do not invent requirements.

Extract:

1. Job title
2. Required skills
3. Preferred or nice-to-have skills
4. Main responsibilities
5. Qualifications

For each required or preferred skill, return:

- name: the skill or technology name
- category: a concise category describing what kind of skill it is
- specificity: whether this is a specific technology or a broader technology category

Use only these specificity values:

- specific_technology
- technology_category
- concept

Examples:

FastAPI
category: framework
specificity: specific_technology

LangGraph
category: framework
specificity: specific_technology

vector databases
category: vector_database
specificity: technology_category

REST APIs
category: api
specificity: technology_category

machine learning
category: machine_learning
specificity: concept

RAG
category: concept
specificity: concept

Important:
- A named framework, library, programming language, database, or tool is usually a specific_technology.
- A broad group such as "vector databases", "REST APIs", or "cloud platforms" is usually a technology_category.
- A broad technical area such as "machine learning", "NLP", or "RAG" is usually a concept.
- Do not invent technologies.
- Use only information explicitly present in the job description.
Job Description:
{job_description}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": JobProfile,
        },
    )

    return JobProfile.model_validate_json(response.text)