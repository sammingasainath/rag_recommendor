from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AssessmentBase(BaseModel):
    """Base model for assessment data."""
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    remote_testing: bool = False
    adaptive_irt: bool = False
    test_types: List[str] = Field(default_factory=list)
    job_levels: List[str] = Field(default_factory=list)
    duration_text: Optional[str] = None
    duration_min_minutes: Optional[int] = None
    duration_max_minutes: Optional[int] = None
    is_untimed: bool = False
    is_variable_duration: bool = False
    languages: List[str] = Field(default_factory=list)
    key_features: List[str] = Field(default_factory=list)


class AssessmentCreate(AssessmentBase):
    """Model for creating a new assessment."""
    pass


class AssessmentUpdate(BaseModel):
    """Model for updating an existing assessment."""
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    remote_testing: Optional[bool] = None
    adaptive_irt: Optional[bool] = None
    test_types: Optional[List[str]] = None
    job_levels: Optional[List[str]] = None
    duration_text: Optional[str] = None
    duration_min_minutes: Optional[int] = None
    duration_max_minutes: Optional[int] = None
    is_untimed: Optional[bool] = None
    is_variable_duration: Optional[bool] = None
    languages: Optional[List[str]] = None
    key_features: Optional[List[str]] = None

    class Config:
        validate_assignment = True


class AssessmentInDB(AssessmentBase):
    """Model for an assessment stored in the database."""
    id: Any  # Accept both string and integer IDs
    embedding: Optional[List[float]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class AssessmentResponse(AssessmentBase):
    """Response model for an assessment."""
    id: Any  # Accept both string and integer IDs
    similarity_score: Optional[float] = None
    relevance_score: Optional[float] = None
    explanation: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True 