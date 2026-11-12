from pydantic import BaseModel, Field
from typing import Optional

class JobCreate(BaseModel):
    title: str
    company: str
    location: str = "Remote"
    description: str
    required_skills: list[str] = []
    experience_level: str = "Entry level"

class AnalyzeRequest(BaseModel):
    resume_id: str
    job_id: str

class ResumeAIRequest(BaseModel):
    resume_id: str
    job_id: Optional[str] = None

class InterviewStartRequest(BaseModel):
    resume_id: str
    job_id: str
    count: int = Field(default=8, ge=1, le=20)

class InterviewAnswerRequest(BaseModel):
    interview_id: str
    question_index: int = Field(ge=0)
    answer: str = Field(min_length=5, max_length=10000)
