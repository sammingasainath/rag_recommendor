from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class JobRequirements(BaseModel):
    """Model for job requirements input."""
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Job description")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    job_level: Optional[str] = Field(None, description="Job level (e.g., Entry, Mid, Senior)")
    remote_work: Optional[bool] = Field(None, description="Whether remote work is required")
    preferred_languages: List[str] = Field(default_factory=list, description="Preferred assessment languages")

class RecommendationRequest(BaseModel):
    """Model for recommendation request."""
    job_requirements: JobRequirements
    top_k: Optional[int] = Field(5, description="Number of recommendations to return")
    min_similarity: Optional[float] = Field(0.5, description="Minimum similarity threshold")
    include_explanation: bool = Field(True, description="Whether to include LLM explanations")

class RecommendationResponse(BaseModel):
    """Model for recommendation response."""
    recommendations: List["AssessmentResponse"]
    query_embedding: Optional[List[float]] = Field(None, description="Vector embedding of the query")
    processing_time: float = Field(..., description="Processing time in seconds")
    total_assessments_searched: int = Field(..., description="Total number of assessments searched")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True 