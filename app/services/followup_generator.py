
import os
from google import genai


def generate_followup_question(
    original_question: str,
    candidate_answer: str,
    knowledge_gaps: list[str],
) -> str:

    if not knowledge_gaps:
        return "No specific knowledge gap was identified. Let's move to the next topic."

    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY")
    )

    prompt = f"""
    You are conducting an adaptive technical interview.

    Original question:
    {original_question}

    Candidate's answer:
    {candidate_answer}

    Knowledge gaps identified:
    {knowledge_gaps}

    Generate exactly ONE follow-up technical question.

    Requirements:
    - Focus on the most important identified knowledge gap.
    - Build on the original question.
    - Test understanding, not memorization alone.
    - Do not repeat the original question.
    - Do not assume the candidate has knowledge not established by the evidence.
    - Return only the question.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )

    if not response.text:
        raise ValueError("Gemini returned an empty follow-up question.")

    return response.text.strip()
