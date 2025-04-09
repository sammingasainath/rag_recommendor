from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from backend.models.assessment import AssessmentResponse

class JobRequirements(BaseModel):
    """Model for job requirements input."""
    title: str = Field(..., description="Job title")
    description: str = Field(..., description="Job description")
    skills: List[str] = Field(default_factory=list, description="Required skills")
    job_level: Optional[str] = Field(None, description="Job level (e.g., Entry, Mid, Senior)")
    remote_work: Optional[bool] = Field(None, description="Whether remote work is required")
    preferred_languages: List[str] = Field(default_factory=list, description="Preferred assessment languages")

class RecommendationFilter(BaseModel):
    """Filter options for recommendation requests."""
    job_levels: Optional[List[str]] = Field(default=None, description="Filter by job levels")
    test_types: Optional[List[str]] = Field(default=None, description="Filter by test types (A, B, C, D, etc.)")
    languages: Optional[List[str]] = Field(default=None, description="Filter by available languages")
    max_duration_minutes: Optional[int] = Field(default=None, description="Maximum duration in minutes")
    duration_type: Optional[str] = Field(default=None, description="Filter by duration type (Fixed, Variable, Untimed)")
    min_similarity: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity threshold (0.0 to 1.0)")
    remote_testing: Optional[bool] = Field(default=None, description="Filter for remote testing availability")

class RecommendationRequest(BaseModel):
    """Request model for assessment recommendations."""
    query: str = Field(..., min_length=3, description="Natural language query describing job requirements")
    top_k: int = Field(5, ge=1, le=20, description="Number of recommendations to return")
    filters: Optional[RecommendationFilter] = Field(default=None, description="Optional filters to apply")

    @field_validator('query')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

class RecommendationResponse(BaseModel):
    """Response model for assessment recommendations."""
    recommendations: List[AssessmentResponse] = Field(default_factory=list, description="List of recommended assessments")
    query_embedding: Optional[List[float]] = Field(default=None, description="Vector embedding of the query")
    processing_time: float = Field(..., description="Processing time in seconds")
    total_assessments: int = Field(..., description="Total number of assessments searched")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the recommendation") 