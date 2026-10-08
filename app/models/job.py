from pydantic import BaseModel, Field


class JobSkill(BaseModel):
    name: str
    category: str
    specificity: str


class JobProfile(BaseModel):
    job_title: str
    required_skills: list[JobSkill] = Field(default_factory=list)
    preferred_skills: list[JobSkill] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)