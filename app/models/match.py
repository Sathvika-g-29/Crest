from pydantic import BaseModel, Field


class SkillMatch(BaseModel):
    skill: str
    job_requirement: str
    requirement_type: str
    resume_evidence: str
    similarity: float
    status: str


class MatchReport(BaseModel):
    matched_skills: list[SkillMatch] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    match_percentage: float = 0.0