
from typing import TypedDict


class InterviewState(TypedDict):
    skill: str
    resume_evidence: str

    current_question: str
    candidate_answer: str

    correctness_score: float
    knowledge_gaps: list[str]

    interview_history: list[dict]

    followup_question: str
    next_action: str
    interview_status: str
