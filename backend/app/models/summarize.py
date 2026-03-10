"""Pydantic models for the summarize endpoint."""

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    """Input schema for POST /api/v1/summarize."""

    job_ids: list[str] = Field(
        ..., min_length=1, description="List of job URLs to summarize"
    )


class RequirementItem(BaseModel):
    """A single requirement with its frequency across job descriptions."""

    name: str
    frequency: int = Field(ge=1)


class RequirementsSummary(BaseModel):
    """Structured requirements extracted from multiple job descriptions."""

    technical_skills: list[RequirementItem] = Field(default_factory=list)
    soft_skills: list[RequirementItem] = Field(default_factory=list)
    education: list[RequirementItem] = Field(default_factory=list)
    certifications: list[RequirementItem] = Field(default_factory=list)
    experience: list[RequirementItem] = Field(default_factory=list)
    total_chunks_analyzed: int = 0


class SummarizeResponse(BaseModel):
    """Output schema for POST /api/v1/summarize."""

    summary: RequirementsSummary
    job_count: int = Field(ge=0, description="Number of jobs analyzed")
    cached: bool = False
