"""Pydantic models for the search endpoint."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Input schema for POST /api/v1/search."""

    title: str = Field(..., min_length=1, max_length=200, description="Job title to search for")
    category: str = Field("", max_length=100, description="Job category or industry")
    keywords: list[str] = Field(default_factory=list, description="Additional search keywords")
    location: str = Field("", max_length=200, description="Geographic location filter")
    date_filter: str = Field(
        "",
        pattern=r"^(day|3days|week|month|)$",
        description="Recency filter: day, 3days, week, month, or empty",
    )
    max_results: int = Field(20, ge=1, le=100, description="Max number of results")


class JobResult(BaseModel):
    """A single job result with match score."""

    title: str
    company: str
    url: str
    snippet: str
    jd_text: str = ""
    date_posted: str = ""
    source: str = ""
    location: str = ""
    match_score: float = Field(0.0, ge=0.0, le=1.0, description="Semantic match score")


class SearchResponse(BaseModel):
    """Output schema for POST /api/v1/search."""

    jobs: list[JobResult]
    total: int
    query_used: str = ""
    cached: bool = False
