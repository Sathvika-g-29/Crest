
from pydantic import BaseModel, Field


class AnswerEvaluation(BaseModel):
    question: str
    candidate_answer: str
    correctness_score: float = Field(ge=0, le=10)
    strengths: list[str] = Field(default_factory=list)
    knowledge_gaps: list[str] = Field(default_factory=list)
    feedback: str
