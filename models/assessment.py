from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class AssessmentBase(BaseModel):
    """Base model for assessment data."""
    name: str = Field(..., description="Name of the assessment")
    url: Optional[str] = Field(None, description="URL to the assessment details")
    remote_testing: bool = Field(False, description="Whether remote testing is available")
    adaptive_irt: bool = Field(False, description="Whether adaptive/IRT is supported")
    test_types: List[str] = Field(default_factory=list, description="Types of tests included (A, B, C, D, E, K, P, S)")
    description: Optional[str] = Field(None, description="Detailed description of the assessment")
    job_levels: List[str] = Field(default_factory=list, description="Suitable job levels")
    duration_text: Optional[str] = Field(None, description="Original duration text")
    duration_minutes: Optional[int] = Field(None, description="Duration in minutes")
    languages: List[str] = Field(default_factory=list, description="Available languages")
    key_features: List[str] = Field(default_factory=list, description="Key features of the assessment")
    source: Optional[str] = Field(None, description="Source of the assessment data")

class AssessmentCreate(AssessmentBase):
    """Model for creating a new assessment."""
    pass

class AssessmentUpdate(AssessmentBase):
    """Model for updating an existing assessment."""
    name: Optional[str] = None

class AssessmentInDB(AssessmentBase):
    """Model for assessment as stored in the database."""
    id: int
    embedding: Optional[List[float]] = Field(None, description="Vector embedding of the assessment")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AssessmentResponse(AssessmentBase):
    """Model for assessment responses in the API."""
    id: int
    similarity_score: Optional[float] = Field(None, description="Similarity score from vector search")
    explanation: Optional[str] = Field(None, description="LLM-generated explanation of relevance")

    class Config:
        from_attributes = True 