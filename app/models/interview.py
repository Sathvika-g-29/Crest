
from pydantic import BaseModel


class InterviewQuestionRequest(BaseModel):
    skill: str


class InterviewQuestion(BaseModel):
    skill: str
    question: str
    resume_evidence: str
