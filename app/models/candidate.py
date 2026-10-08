from pydantic import BaseModel, Field

class Skill(BaseModel):
    name: str
    category: str
    specificity: str
    evidence: str = ""

class Project(BaseModel):
    name: str
    description: str
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str
    institution: str
    details: str = ""


class Experience(BaseModel):
    role: str
    company: str
    description: str


class CandidateProfile(BaseModel):
    name: str
    skills: list[Skill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)